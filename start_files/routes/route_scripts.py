from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from start_files.models.users.users import SessionLocal, User, Base, engine
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from selenium import webdriver
from datetime import datetime
import logging
import asyncio
import random
import time
import csv
import re
import os

# Load environment variables
load_dotenv()
BRIGHTMLS_USERNAME = os.getenv("BRIGHTMLS")
BRIGHTMLS_PASSWORD = os.getenv("PASSWORD")

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def get_end_time_and_elapsed(start_time):
    end_time = time.time()
    elapsed = end_time - start_time
    formatted_end_time = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
    formatted_elapsed_time = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
    return formatted_end_time, formatted_elapsed_time


# Set up Chrome options
def setup_options(max_retries, delay) -> webdriver.Chrome:
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    service = ChromeService(executable_path='/usr/bin/chromedriver')

    for attempt in range(max_retries):
        try:
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except WebDriverException:
            print(f"driver retrying.. {attempt + 1} ")
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
    raise RuntimeError("Failed to start Chrome after multiple attempts")


def load_page(max_images, item, timeout, max_retries, delay):
    attempt = 0
    mls = item[1]
    image_link_full = []
    driver = None
    while attempt < max_retries:
        try:    
            driver = setup_options(max_retries, delay)
            
            logger.info(f"Setting up driver for {mls}")
            logger.info(f"{mls} driver set")
            
            logger.info(f"Loading {mls} page...")
            driver.get("https://matrix.brightmls.com/Matrix/Search/ResidentialLease/ResidentialLease")

            # Ensure username field is interactable
            logger.info(f"Beginning login for MLS {mls}.")
            username_field = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, "username")))
            driver.execute_script("arguments[0].scrollIntoView(true);", username_field)
            driver.execute_script("arguments[0].click();", username_field)
            username_field.send_keys(BRIGHTMLS_USERNAME)
            
            # Ensure password field is interactable
            password_field = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "password")))
            driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
            driver.execute_script("arguments[0].click();", password_field)
            password_field.send_keys(BRIGHTMLS_PASSWORD)
            
            # Ensure login button is interactable
            login_button = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".css-yck31-root-root-root")))
            driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
            driver.execute_script("arguments[0].click();", login_button)
        
            logger.info(f"Starting to search for MLS {mls}")
            search_bar_locator = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, "ctl01$m_ucSpeedBar$m_tbSpeedBar")))
            driver.execute_script("arguments[0].scrollIntoView(true);", search_bar_locator)
            driver.execute_script("arguments[0].click();", search_bar_locator)
            search_bar_locator.send_keys(mls)

            logger.info(f"Entering {mls} in search bar")
            search_bar_submit = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "ctl01_m_ucSpeedBar_m_lnkGo")))
            driver.execute_script("arguments[0].scrollIntoView(true);", search_bar_submit)
            driver.execute_script("arguments[0].click();", search_bar_submit)
            logger.info(f"Submitting search entry.")
            

            try:
                time.sleep(1)
                logger.debug("Waiting for confirmation listing element to be clickable")
                select_listing = driver.find_element(by=By.XPATH, value="//a[contains(text(), 'Listing ID')]")
                if select_listing:
                    driver.execute_script("arguments[0].scrollIntoView(true);", select_listing)
                    driver.execute_script("arguments[0].click();", select_listing)
                    logger.info(f"Location for {mls} confirmed")
            except NoSuchElementException:
                logger.info("Confirmation listing element not found, moving on")

            
            click_entry = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, '//td[@class="NoPrint checkboxTableRow d25m0"]//input[@type="checkbox"]')))
            driver.execute_script("arguments[0].scrollIntoView(true);", click_entry)
            driver.execute_script("arguments[0].click();", click_entry)
            logger.info(f"Entry submitted. Clicking {mls} on results page")
            
            dropdown_element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, 'm_ucDisplayPicker_m_ddlDisplayFormats')))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", dropdown_element)
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.ID, 'm_ucDisplayPicker_m_ddlDisplayFormats')))
            dropdown = Select(dropdown_element)
            dropdown.select_by_visible_text("Agent Full")
            
            logger.info("Selected 'Agent Full' successfully")
            formula_span = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, "//span[text()='Click to Show Photos']")))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", formula_span)
            driver.execute_script("arguments[0].click();", formula_span)
            
            logger.info(f"Clicking image section for {mls}")
            images_locator = (By.XPATH, '//font[@class="IV_Single"]//img[@class="IV_Image"]')
            WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located(images_locator))
            all_imgs = driver.find_elements(*images_locator)
            all_links = [tag.get_attribute('src') for tag in all_imgs[:max_images]]
            if not all_links:
                logger.warning(f"MLS {mls} has no images.")
            else:
                image_link_full.append([mls, all_links])
            
            logger.info(f"Completed image extraction for MLS {mls}.")    

            if len(all_links) == 0:
                logger.warning(f"Skipped. MLS {mls} has no images.")
            else:
                image_link_full.append([mls, all_links])

            if driver is not None:
                driver.quit()
            
            logger.info('Starting database session')    
            db: Session = None
            try:
                db = SessionLocal()
                user = db.query(User).filter_by(mls=mls).first()
                if user:
                    # Update existing user
                    user.mls = mls
                else:
                    # Create new listing
                    listing = User(
                        mls=mls,
                        address=f"{item[2]}, {item[5]}, {item[6]} {item[7]}",
                        price=item[0],
                        description=item[14],
                        availability=item[3],
                        image_list=image_link_full[0][1] if image_link_full else []
                    )
                    for attempt in range(max_retries):
                        try:
                            db.add(listing)
                            db.commit()
                            logger.info(f"{mls} Added to database!")
                            return
                        except (OperationalError, TimeoutError):
                            logger.error(f" {mls} database error. Attempt {attempt + 1}/{max_retries}")
                            db.rollback()
                            sleep_time = (2 ** attempt) + random.uniform(0, 1)  
                            time.sleep(sleep_time)
            finally:
                if db:
                    db.close()

        except (WebDriverException, TimeoutException):
            logger.error(f"Attempt {attempt + 1} failed")
            attempt += 1
            if attempt < max_retries:
                sleep_time = delay * (2 ** (attempt - 1)) 
                logger.info(f"Retrying in {sleep_time} seconds...")
                driver.refresh()
                time.sleep(sleep_time)
            else:
                logger.error("Max retries exceeded. Could not load page.")
                raise


# Sort CSV by price
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
    return sorted(all_data, key=lambda x: x[0])

# Download images with concurrency
async def start_cpncurrency( max_retries, delay, timeout, concurrency_limit, max_images, sorted_results: list) -> list:
    semaphore = asyncio.Semaphore(concurrency_limit)
    async def download_image_with_semaphore(item):
        async with semaphore:
            return await loop.run_in_executor(executor, load_page, max_images, item, timeout,  max_retries, delay)
    logger.info("About to begin concurrency"), 
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [download_image_with_semaphore(item) for item in sorted_results]
        image_link_full = await asyncio.gather(*tasks)
        return image_link_full


# Gather images and MLS data
async def loop_task(concurrency_limit, timeout, max_images, max_price, max_retries, delay) -> None:
    sorted_results = await sorted_csv_by_price(max_price)
    logger.info('Clearing and recreating database tables')
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    await start_cpncurrency( max_retries, delay, timeout, concurrency_limit, max_images, sorted_results)


# Synchronous entry point
def start_task(concurrency_limit, timeout, max_images, max_price, max_retries, delay):
    start_time = time.time()
    logger.info(f"{datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(loop_task(concurrency_limit, timeout, max_images, max_price, max_retries, delay))
    finally:
        loop.close()
        end_time, elapsed_time = get_end_time_and_elapsed(start_time)
        logger.info(f"End Time: {end_time}") 
        logger.info(f"Elapsed Time: {elapsed_time}")