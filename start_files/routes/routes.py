from fastapi import APIRouter, Form, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from start_files.models.users.users import SessionLocal, User
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
import csv
import re
from sqlalchemy.exc import SQLAlchemyError
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

router = APIRouter()

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Load environment variables
load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT = os.getenv("RECIPIENT")
SENDER = os.getenv("SENDER")
BRIGHTMLS_USERNAME = os.getenv("BRIGHTMLS")
BRIGHTMLS_PASSWORD = os.getenv("PASSWORD")

@router.post("/contact")
async def handle_contact_form(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    general_inquiry: str = Form(...)
):
    logger.info(f"Received contact form submission from {email}")

    message = Mail(
        from_email=SENDER,
        to_emails=RECIPIENT,
        subject='New Contact Form Submission',
        html_content=f"""
        <p>First Name: {first_name}</p>
        <p>Last Name: {last_name}</p>
        <p>Email: {email}</p>
        <p>Phone: {phone}</p>
        <p>General Inquiry: {general_inquiry}</p>
        """
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"SendGrid response status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending email: {e}")

    logger.info("Contact form submission successful, redirecting user.")
    return RedirectResponse(url="/contact", status_code=303)


@router.get("/", response_class=HTMLResponse, name="home")
async def read_root(request: Request):
    logger.info("Rendering home page")
    templates = request.app.state.templates
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/rentals", response_class=HTMLResponse, name="rentals")
async def rentals(request: Request):
    logger.info("Rendering rentals page")
    templates = request.app.state.templates
    return templates.TemplateResponse("rentals.html", {"request": request})

@router.get("/buying", response_class=HTMLResponse, name="buying")
async def buying(request: Request):
    logger.info("Rendering buying page")
    templates = request.app.state.templates
    return templates.TemplateResponse("buying.html", {"request": request})

@router.get("/resources", response_class=HTMLResponse, name="resources")
async def resources(request: Request):
    logger.info("Rendering resources page")
    templates = request.app.state.templates
    return templates.TemplateResponse("resources.html", {"request": request})

@router.get("/contact", response_class=HTMLResponse, name="contact")
async def contact(request: Request):
    logger.info("Rendering contact page")
    templates = request.app.state.templates
    return templates.TemplateResponse("contact.html", {"request": request})

# Define your asynchronous functions for background processing
async def setup_options() -> webdriver.Chrome:
    options = ChromeOptions()
    options.add_argument('--headless')  # Run headless for Raspberry Pi
    options.add_argument('--no-sandbox')

    # Use Chromium's chromedriver
    service = ChromeService(executable_path='/usr/lib/chromium-browser/chromedriver')

    driver = webdriver.Chrome(service=service, options=options)
    return driver

async def login(driver, timeout: int, username: str, password: str):
    driver.get("https://matrix.brightmls.com/Matrix/Search/ResidentialLease/ResidentialLease")

    try:
        element_present = EC.element_to_be_clickable((By.NAME, "username"))
        WebDriverWait(driver, timeout).until(element_present)
        field_username = driver.find_element(by=By.NAME, value="username")
        field_username.send_keys(username)
        field_password = driver.find_element(by=By.ID, value="password")
        field_password.send_keys(password)
        button = driver.find_element(by=By.CSS_SELECTOR, value=".css-yck31-root-root-root")
        button.click()
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

async def sorted_csv_by_price(max_price: float = None) -> list:
    csv_path = "/var/www/html/fastapi_project/brightscrape/Standard_Export.csv"
    all_data = []

    async def preprocess_price(price_str: str) -> float:
        match = re.search(r'\d+', price_str.replace(',', ''))
        if match:
            return float(match.group())
        return float('inf')

    with open(csv_path, mode='r') as data:
        data_content = csv.reader(data, delimiter=',')
        next(data_content, None)
        for row in data_content:
            mls = row[0]
            street_unit = row[1]
            status = row[3]
            price = await preprocess_price(row[6])
            list_date = row[11]
            city = row[22]
            state = row[23]
            zip_code = row[24]
            listing_office = row[37]
            listing_office_number = row[38]
            listing_agent = row[39]
            listing_agent_number = row[40]
            listing_agent_email = row[41]
            agent_remarks = row[42]
            public_remarks = row[44]

            if (max_price is None or price < max_price) and state == 'VA':
                all_data.append((price, mls, street_unit, status, list_date, city, state, zip_code,
                                listing_office, listing_office_number, listing_agent, listing_agent_number,
                                listing_agent_email, agent_remarks, public_remarks))

    all_data_sorted = sorted(all_data, key=lambda x: x[0])
    return all_data_sorted

async def download_images(driver, timeout: int, sorted_results: list) -> list:
    max_images = 10
    image_link_full = []
    for item in sorted_results:
        mls = item[1]
        try:
            search_bar_locator = (By.NAME, "ctl01$m_ucSpeedBar$m_tbSpeedBar")
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(search_bar_locator))
            search_mls = driver.find_element(*search_bar_locator)
            search_mls.clear()
            search_mls.send_keys(mls)

            go_button_locator = (By.ID, "ctl01_m_ucSpeedBar_m_lnkGo")
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(go_button_locator))
            go_button = driver.find_element(*go_button_locator)
            go_button.click()

            mls_details_locator = (By.XPATH, '//td[@class="d25m6"]//span[@class="d25m1"]')
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(mls_details_locator))
            mls_record = driver.find_element(*mls_details_locator)
            mls_record.click()

            Find_click_to_open = (By.XPATH, '//*[@class="d76m22"]//span[@class="formula"]')
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(Find_click_to_open))
            open_images = driver.find_element(*Find_click_to_open)
            driver.execute_script("arguments[0].scrollIntoView(true);", open_images)
            open_images.click()

            images_locator = (By.XPATH, '//font[@class="IV_Single"]//img[@class="IV_Image"]')
            WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located(images_locator))
            all_imgs = driver.find_elements(*images_locator)

            all_links = []
            for i, tag in enumerate(all_imgs[:max_images], start=1):
                try:
                    image_link = tag.get_attribute('src')
                    all_links.append(image_link)
                except Exception as e:
                    logger.error(f"Failed to gather image URL: {i} for MLS {mls}: {e}")

            if len(all_links) == 0:
                logger.warning(f"MLS {mls} has no images.")
            else:
                logger.info(f"Completed image extractions for MLS {mls}, found {len(all_imgs)} images.")
            await asyncio.sleep(1)
            image_link_full.append([mls, all_links])
        except Exception as e:
            logger.error(f"Exception: Unexpected error for MLS {mls}: {e}")
    return image_link_full

async def gather_images_and_mls_data() -> None:
    timeout = 100
    max_price = 1000
    driver = await setup_options()
    db: Session = SessionLocal()  # Create a new session for database operations
    try:
        await login(driver, timeout, BRIGHTMLS_USERNAME, BRIGHTMLS_PASSWORD)
        sorted_results = await sorted_csv_by_price(max_price)
        image_links = await download_images(driver, timeout, sorted_results)

        mls_links_dict = {name: links for name, links in image_links}

        for item in sorted_results:
            name = item[1]
            images = mls_links_dict.get(name, [])
            user = db.query(User).filter_by(mls=name).first()
            if user:
                user.address = f"{item[2]}, {item[5]}, {item[6]} {item[7]}"
                user.price = item[0]
                user.description = item[14]
                user.availability = item[3]
                user.image_list = images
            else:
                user = User(
                    mls=name,
                    address=f"{item[2]}, {item[5]}, {item[6]} {item[7]}",
                    price=item[0],
                    description=item[14],
                    availability=item[3],
                    image_list=images
                )
                db.add(user)
        
        db.commit()

    except SQLAlchemyError as e:
        logger.error(f"Database error during MLS data gathering: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred during MLS data gathering")
    except Exception as e:
        logger.error(f"Error during MLS data gathering: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred during MLS data gathering")
    finally:
        driver.quit()
        db.close()  # Ensure the session is closed

@router.get("/mls-data", response_model=dict)
async def get_mls_data(background_tasks: BackgroundTasks):
    logger.info("Starting MLS data gathering task")
    background_tasks.add_task(gather_images_and_mls_data)
    return JSONResponse(content={"message": "MLS data gathering task started in the background"})