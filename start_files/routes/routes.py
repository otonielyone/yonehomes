from concurrent.futures import ThreadPoolExecutor
import shutil
import sys
import time
from fastapi import APIRouter, Form, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from start_files.models.users.users import SessionLocal, User, Base, engine
import logging
from selenium.webdriver.support.ui import Select
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
import csv
from sqlalchemy.exc import OperationalError
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
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

load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT = os.getenv("RECIPIENT")
SENDER = os.getenv("SENDER")
BRIGHTMLS_USERNAME = os.getenv("BRIGHTMLS")
BRIGHTMLS_PASSWORD = os.getenv("PASSWORD")

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def setup_options() -> webdriver.Chrome:
    logger.info("Setting up Chrome options")
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--window-size=1920,1080')
    service = ChromeService(executable_path='/usr/lib/chromium-browser/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    logger.info("Chrome options setup complete")
    return driver


async def async_setup_options() -> webdriver.Chrome:
    logger.info("Setting up Chrome options")
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--window-size=1920,1080')
    options.add_experimental_option("prefs", {
        "download.default_directory": "/home/oyone/Downloads/",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    service = ChromeService(executable_path='/usr/lib/chromium-browser/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    logger.info("Chrome options setup complete")
    return driver

def login(driver: webdriver.Chrome, timeout: int, username: str, password: str):
    logger.info("About to Begin Login")
    try:
        # Ensure username field is interactable
        username_field = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, "username")))
        driver.execute_script("arguments[0].scrollIntoView(true);", username_field)
        driver.execute_script("arguments[0].click();", username_field)
        username_field.send_keys(username)
        
        # Ensure password field is interactable
        password_field = driver.find_element(By.ID, "password")
        driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
        driver.execute_script("arguments[0].click();", password_field)
        password_field.send_keys(password)
        
        # Ensure login button is interactable
        login_button = driver.find_element(By.CSS_SELECTOR, ".css-yck31-root-root-root")
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        driver.execute_script("arguments[0].click();", login_button)

    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise


async def async_login(driver: webdriver.Chrome, timeout: int, username: str, password: str):
    logger.info("About to Begin Login")
    driver.get("https://matrix.brightmls.com/Matrix/Search/ResidentialLease/ResidentialLease")
    try:
        # Ensure username field is interactable
        username_field = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, "username")))
        driver.execute_script("arguments[0].scrollIntoView(true);", username_field)
        driver.execute_script("arguments[0].click();", username_field)
        username_field.send_keys(username)
        
        # Ensure password field is interactable
        password_field = driver.find_element(By.ID, "password")
        driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
        driver.execute_script("arguments[0].click();", password_field)
        password_field.send_keys(password)
        
        # Ensure login button is interactable
        login_button = driver.find_element(By.CSS_SELECTOR, ".css-yck31-root-root-root")
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        driver.execute_script("arguments[0].click();", login_button)

    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise

async def navigate_to_search_page(driver, timeout):
    logger.info("Navigating to search page")
    try:
        logger.debug("Waiting for checkbox to be clickable")
        element_present = EC.element_to_be_clickable((By.NAME, "Fm8_Ctrl39_LB"))
        WebDriverWait(driver, timeout).until(element_present)
        
        unclick_coming_soon = driver.find_element(by=By.NAME, value="Fm8_Ctrl39_LB")
        logger.debug("Scrolling element into view")
        driver.execute_script("arguments[0].scrollIntoView(true);", unclick_coming_soon)
        logger.debug("Attempting to click the element")
        unclick_coming_soon.click()

        logger.debug("Waiting for distance field to be clickable")
        element_present = EC.element_to_be_clickable((By.CSS_SELECTOR, ".mapSearchDistance"))
        WebDriverWait(driver, timeout).until(element_present)
        field_miles = driver.find_element(by=By.CSS_SELECTOR, value=".mapSearchDistance")
        field_miles.send_keys('25')

        logger.debug("Waiting for location field to be clickable")
        element_present = EC.element_to_be_clickable((By.ID, "Fm8_Ctrl33_TB"))
        WebDriverWait(driver, timeout).until(element_present)
        field_location = driver.find_element(by=By.ID, value="Fm8_Ctrl33_TB")
        field_location.send_keys('Manassas, VA 20109, USA')

        logger.debug("Waiting for confirmation location element to be clickable")
        element_present = EC.element_to_be_clickable((By.CSS_SELECTOR, ".disambiguation"))
        WebDriverWait(driver, timeout).until(element_present)
        confirm_location = driver.find_element(by=By.CSS_SELECTOR, value=".disambiguation")
        if confirm_location:
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(confirm_location, 5, 5)
            actions.click()
            actions.perform()
            logger.info("Location confirmed")

        logger.debug("Waiting for results tab to be clickable")
        element_present = EC.element_to_be_clickable((By.ID, "m_ucResultsPageTabs_m_pnlResultsTab"))
        WebDriverWait(driver, timeout).until(element_present)
        results = driver.find_element(by=By.ID, value="m_ucResultsPageTabs_m_pnlResultsTab")
        results.click()
        logger.info("Results tab clicked successfully")
    
    except TimeoutException:
        logger.error("Timeout while waiting for elements.")
        sys.exit()
    except ElementClickInterceptedException as e:
        logger.error(f"ElementClickInterceptedException: {e}")
        sys.exit()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit()

async def clear_database():
        # Clear and recreate the database schema
        logger.info('Clearing and recreating database tables')
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        

async def export_results():
    logger.info("Starting export_results function")
    driver = await async_setup_options()
    timeout = 100
    await async_login(driver, timeout, BRIGHTMLS_USERNAME, BRIGHTMLS_PASSWORD)
    await navigate_to_search_page(driver, timeout)

    try:
        element_present = EC.element_to_be_clickable((By.ID, "m_lnkCheckAllLink"))
        WebDriverWait(driver, timeout).until(element_present)
        all = driver.find_element(by=By.ID, value="m_lnkCheckAllLink")
        driver.execute_script("arguments[0].click();", all)
        logger.info("'Check All Results Entries' link clicked successfully")

        pre_export = driver.find_element(by=By.ID, value="m_lbExport")
        driver.execute_script("arguments[0].click();", pre_export)
        logger.info("'Submit Export' button clicked successfully")

        await asyncio.sleep(2)

        select_element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//select[@id='m_ddExport']"))
        )
        driver.execute_script("arguments[0].click();", select_element)
        select_element.send_keys("s")
        select_element.send_keys(Keys.ENTER)
        logger.info("Standard Export selected from dropdown")

        export = driver.find_element(by=By.ID, value="m_btnExport")
        driver.execute_script("arguments[0].click();", export)
        logger.info("'Export' button clicked successfully")

        download_dir = "/home/oyone/Downloads/"
        csv_path1 = os.path.join(download_dir, "Standard Export.csv")
        csv_path2 = "/var/www/html/fastapi_project/brightscrape/Standard Export.csv"

        while not os.path.exists(csv_path1):
            await asyncio.sleep(1)
        logger.info(f"File downloaded: {csv_path1}")
        
        shutil.move(csv_path1, csv_path2)
        logger.info(f"File moved from {csv_path1} to {csv_path2}")
 
    except Exception as e:
        logger.error(f"Error during export results: {e}")
        raise HTTPException(status_code=500, detail="Error during export results")
    
    logger.info('Done fetching csv')
    return "CSV file has been downloaded and moved successfully!"
    

async def sorted_csv_by_price(max_price) -> list:
    csv_path = "/var/www/html/fastapi_project/brightscrape/Standard Export.csv"
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


def download_images_for_item(item, timeout, max_images) -> list:
    mls = item[1]
    image_link_full = []
    driver  = None
    
    try:
        driver = setup_options()
        driver.save_screenshot('debug_screenshot1.png')

        logger.info("Grabbing search page")
        driver.get("https://matrix.brightmls.com/Matrix/Search/ResidentialLease/ResidentialLease")

        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        page_title = driver.title
        logger.info("Page title confirm.")

        if "SSO | Bright MLS" in page_title:
            logger.info("Page title indicates login is required.")
            login(driver, timeout, BRIGHTMLS_USERNAME, BRIGHTMLS_PASSWORD)
    
    finally:
        logger.info("Beginning page query.")
        driver.save_screenshot('debug_screenshot2.png')

    search_bar_locator = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, "ctl01$m_ucSpeedBar$m_tbSpeedBar")))
    driver.execute_script("arguments[0].scrollIntoView(true);", search_bar_locator)
    driver.execute_script("arguments[0].click();", search_bar_locator)
    search_bar_locator.send_keys(mls)
    logger.info(f"Entering {item[1]} in search bar")
    
    search_bar_submit = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "ctl01_m_ucSpeedBar_m_lnkGo")))
    driver.execute_script("arguments[0].scrollIntoView(true);", search_bar_submit)
    driver.execute_script("arguments[0].click();", search_bar_submit)
    logger.info(f"Submitting search entry.")
    
    click_entry = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, '//td[@class="NoPrint checkboxTableRow d25m0"]//input[@type="checkbox"]')))
    driver.execute_script("arguments[0].scrollIntoView(true);", click_entry)
    driver.execute_script("arguments[0].click();", click_entry)
    logger.info(f"Entry submitted. clicking  {item[1]} on results page")
    
    dropdown_element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, 'm_ucDisplayPicker_m_ddlDisplayFormats')))
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", dropdown_element)
    WebDriverWait(driver, timeout).until(EC.visibility_of(dropdown_element))
    WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.ID, 'm_ucDisplayPicker_m_ddlDisplayFormats')))
    dropdown = Select(dropdown_element)
    dropdown.select_by_visible_text("Agent Full")
    logger.info("Selected 'Agent Full' successfully")
    
    formula_span = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, "//span[text()='Click to Show Photos']")))
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", formula_span)
    
    WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Click to Show Photos']")))
    driver.execute_script("arguments[0].click();", formula_span)
    logger.info(f" Clicking image section for {item[1]}")

    images_locator = (By.XPATH, '//font[@class="IV_Single"]//img[@class="IV_Image"]')
    WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located(images_locator))
    all_imgs = driver.find_elements(*images_locator)
    all_links = [tag.get_attribute('src') for tag in all_imgs[:max_images]]
    
    if len(all_links) == 0:
        logger.warning(f"MLS {mls} has no images.")
    else:
        logger.info(f"Completed image extraction for MLS {mls}, found {len(all_links)} images.")
    image_link_full.append([mls, all_links])
    driver.quit()

    
    try:
        logger.info('Starting database session')
        db: Session = SessionLocal()
                
        listing = User(
            mls=mls,
            address=f"{item[2]}, {item[5]}, {item[6]} {item[7]}",
            price=item[0],
            description=item[14],
            availability=item[3],
            image_list=image_link_full[0][1] if image_link_full else []
        )

        MAX_RETRIES = 5
        RETRY_DELAY = 1

        for attempt in range(MAX_RETRIES):
            try:
                # Use a context manager to ensure the session is handled correctly
                with db as db_session:
                    db_session.add(listing)
                    db_session.commit()
                logger.info(f"Successfully inserted data into the database on attempt {attempt + 1}.")
                return
            except OperationalError as e:
                logger.error(f"Database is locked. Attempt {attempt + 1} of {MAX_RETRIES}. Error: {e}")
                time.sleep(RETRY_DELAY)
            except Exception as e:
                # Handle other possible exceptions
                logger.error(f"Unexpected error during database insertion: {e}")
                raise
        logger.error("Max retries exceeded. Could not insert data into the database.")
        raise RuntimeError("Failed to insert data after several retries.")
    
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
            

async def download_images(timeout, concurrency_limit, max_images, sorted_results: list) -> list:
    semaphore = asyncio.Semaphore(concurrency_limit)
    async def download_image_with_semaphore(item):
        async with semaphore:
            return await loop.run_in_executor(executor, download_images_for_item, item, timeout, max_images)
    logger.info("About to begin concurrency")
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [download_image_with_semaphore(item) for item in sorted_results]
        image_link_full = await asyncio.gather(*tasks)
        return image_link_full


def sync_gather_images_and_mls_data(concurrency_limit, timeout, max_images, max_price):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(gather_images_and_mls_data(concurrency_limit, timeout, max_images, max_price))
    finally:
        loop.close()


async def gather_images_and_mls_data(concurrency_limit, timeout, max_images, max_price) -> None:
    #await export_results()
    sorted_results = await sorted_csv_by_price(max_price)
    await clear_database()
    await download_images(timeout, concurrency_limit, max_images, sorted_results)




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


@router.get("/get-csv", response_class=JSONResponse, name="export")
async def export_results_endpoint(background_tasks: BackgroundTasks):
    logger.info("Starting CSV export task in the background")
    background_tasks.add_task(export_results)  # Do not await here
    return JSONResponse(content={"message": "CSV export task started in the background"})

@router.get("/count-list", response_class=JSONResponse, name="filter")
async def sort_csv_endpoint(max_price):
    logger.info("Starting CSV sort task in the background")
    sorted = await sorted_csv_by_price(max_price)
    return f"This sorted list has {len(sorted)} listings."

@router.get("/populate-database", response_model=dict, name="import")
async def get_mls_data(background_tasks: BackgroundTasks, concurrency_limit: int = 5, timeout: int = 120, max_images: int = 50, max_price: int = 2500):
    logger.info("Starting MLS data gathering task")
    background_tasks.add_task(sync_gather_images_and_mls_data, concurrency_limit, timeout, max_images, max_price)
    return JSONResponse(content={"message": "MLS data gathering task started in the background"})
    
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

