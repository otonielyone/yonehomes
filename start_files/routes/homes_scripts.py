from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException, StaleElementReferenceException
from start_files.models.mls.homes_db_section import homes_sessionLocal, init_homes_db, init_homes_db_temp, Mls_homes_temp
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from start_files.routes.export_homes_scripts import export_homes
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from contextlib import contextmanager
from dotenv import load_dotenv
from selenium import webdriver
from datetime import datetime
from io import BytesIO
from PIL import Image
import requests
import hashlib
import sqlite3
import logging
import asyncio
import shutil 
import time
import csv
import re
import os

load_dotenv()
BRIGHTMLS_USERNAME = os.getenv("BRIGHTMLS")
BRIGHTMLS_PASSWORD = os.getenv("PASSWORD")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def purge_cloudflare_cache():
    response = requests.post(
        f'https://api.cloudflare.com/client/v4/zones/{os.getenv("CLOUDFLARE_ZONE")}/purge_cache',
        headers={
            'Authorization': f'Bearer {os.getenv("CLOUDFLARE_API_TOKEN")}',
            'Content-Type': 'application/json',
        },
        json={'purge_everything': True}
    )
    return response.json()

print(purge_cloudflare_cache())


def clean_and_rename_directories():
    base_dir = 'start_files/static/homes_images/'
    csv_path = "brightscrape/Export_homes.csv"

    if os.path.exists(csv_path):
        os.remove(csv_path)
        logger.info("Removed CSV.")

    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)
            
        if '-pending' in folder:
            new_name = folder[:-len('-pending')]
            new_item_path = os.path.join(base_dir, new_name)

            if os.path.exists(new_item_path):
                logger.info(f"Removing existing directory to allow overwrite: {new_item_path}")
                shutil.rmtree(new_item_path) 
                
            logger.info(f"Renaming directory: {folder} to {new_item_path}")
            os.rename(folder_path, new_item_path)



def replace_and_cleanup_tables():
    original_table = 'mls_homes'
    temp_table = 'mls_homes_temp'
    
    try:
        conn = sqlite3.connect('brightscrape/brightmls.db')
        cursor = conn.cursor()

        cursor.execute(f"DELETE FROM {original_table}")
        cursor.execute(f"INSERT INTO {original_table} SELECT * FROM {temp_table}")
        cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
        conn.commit()
        logger.info(f"Table '{original_table}' successfully overwritten by '{temp_table}'.")
        
    except sqlite3.Error as e:
        logger.info(f"SQLite error: {e}")

    finally:
        if conn:
            conn.close()


def get_end_time_and_elapsed(start_time):
    end_time = time.time()
    elapsed = end_time - start_time
    formatted_end_time = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
    formatted_elapsed_time = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
    return formatted_end_time, formatted_elapsed_time


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
            logger.error(f"Driver retrying.. {attempt + 1}")
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)

    raise RuntimeError("Failed to start Chrome after multiple attempts")


<<<<<<< HEAD

=======
>>>>>>> main
def sorted_homes_by_price(max_price) -> list:
    csv_path = "brightscrape/Export_homes.csv"
    logger.info('Found csv for homes')
    all_data = []
    
    max_retries = 3
    delay = 2

    def preprocess_price(price_str: str) -> float:
        match = re.search(r'\d+', price_str.replace(',', ''))
        if match:
            return float(match.group())
        return float('inf')

    logger.info('Opening csv')
    
    for attempt in range(max_retries):
        try:
            with open(csv_path, mode='r') as data:
                data_content = csv.reader(data, delimiter=',')
                next(data_content, None)
                for row in data_content:
                    mls = row[0]
                    street_unit = row[1]
                    status = row[3]
                    price = preprocess_price(row[6])
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
                    acres = row[60]
                    age = row[73]
                    int_sqft = row[74]
                    bedrooms = row[79]
                    baths = row[80]
                    bath_full = row[81]
                    bath_half = row[82]
                    fireplace = row[97]
                    basement = row[104]
                    garage = row[109]
                    garage_spaces = row[110]

                    if (max_price is None or price < max_price) and state == 'VA':
                        all_data.append((price, mls, street_unit, status, list_date, city, state, zip_code,
                                         listing_office, listing_office_number, listing_agent, listing_agent_number,
                                         listing_agent_email, agent_remarks, public_remarks, bedrooms, baths, bath_full, bath_half, acres, age, int_sqft, fireplace, basement, garage, garage_spaces))
            logger.info('Finished reading csv')
            return sorted(all_data, key=lambda x: x[0])
        
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)

    raise Exception(f"Failed to read CSV after {max_retries} attempts")





@contextmanager
def get_db_session_pending():
    db = homes_sessionLocal()
    yield db 
    if db:
        db.close()


def generate_hash(item_details, image_urls):
    return hashlib.sha256(f"{item_details}-{len(image_urls)}".encode()).hexdigest()

def save_images(all_imgs, save_dir, max_images):
    for i, img in enumerate(all_imgs[:max_images]):
        img_url = img.get_attribute('src')
        if img_url:
            response = requests.get(img_url)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img.save(os.path.join(save_dir, f'{i + 1}.webp'), 'WEBP')

def add_listing_to_db(db, mls, item, current_hash, img_count):
    listing = Mls_homes_temp(
        mls=mls,
        address=f"{item[2]}, {item[5]}, {item[6]} {item[7]}",
        price=item[0],
        description=item[14],
        availability=item[3],
        bedrooms=item[15],
        bath=item[16],
        full=item[17],
        half=item[18],
        acres=item[19],
        age=item[20],
        sqft=item[21],
        fireplace=item[22],
        basement=item[23],
        garage=item[24],
        spaces=item[25],
        count=img_count,
        hash=current_hash
    )
    db.add(listing)
    db.commit()

def update_listing_in_db(db, listing_item, item, current_hash, img_count):
    listing_item.address = f"{item[2]}, {item[5]}, {item[6]} {item[7]}"
    listing_item.price = item[0]
    listing_item.description = item[14]
    listing_item.availability = item[3]
    listing_item.bedrooms = item[15]
    listing_item.bath = item[16]
    listing_item.full = item[17]
    listing_item.half = item[18]
    listing_item.acres = item[19]
    listing_item.age = item[20]
    listing_item.sqft = item[21]
    listing_item.fireplace = item[22]
    listing_item.basement = item[23]
    listing_item.garage = item[24]
    listing_item.spaces = item[25]
    listing_item.count = img_count
    listing_item.hash = current_hash
    db.commit()

def check_and_recreate_images(db, mls, all_imgs, max_images):
    in_place = f'start_files/static/homes_images/{mls}/'
    if not os.path.exists(in_place):
        logger.info(f"Pending directory for {mls} does not exist, updating listing.")
        save_dir = f'start_files/static/homes_images/{mls}-pending/'
        os.makedirs(save_dir, exist_ok=True)
        save_images(all_imgs, save_dir, max_images)
        logger.info(f"Recreated image data for {mls}")

def clean_up_temp_listings(sorted_results):
    with get_db_session_pending() as db:
        results = {item[1] for item in sorted_results}
        temp_listings = db.query(Mls_homes_temp).all()
        for listing_item in temp_listings:
            if listing_item.mls not in results:
                logger.info(f"{listing_item.mls} not in sorted results. Removing from temp database.")
                db.delete(listing_item)
                db.commit()
                logger.info(f"Removed {listing_item.mls} from temp database.")

def load_page(max_images, min_images, item, timeout, max_retries, delay):
    mls = item[1]
    attempt = 0

    while attempt < max_retries:
        driver = None
        db = None
        
        logger.info(f"Setting up driver for MLS {mls}")
        try:
            driver = setup_options(max_retries, delay)
            driver.get("https://matrix.brightmls.com/Matrix/Search/ResidentialSale/Residential")

            logger.info(f"Beginning login for MLS {mls}.")
            username_field = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, "username")))
            driver.execute_script("arguments[0].scrollIntoView(true);", username_field)
            username_field.send_keys(BRIGHTMLS_USERNAME)

            password_field = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "password")))
            driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
            password_field.send_keys(BRIGHTMLS_PASSWORD)

            login_button = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".css-yck31-root-root-root")))
            driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
            driver.execute_script("arguments[0].click();", login_button)

            logger.info(f"Starting to search for MLS {mls}")
            search_bar_locator = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, "ctl01$m_ucSpeedBar$m_tbSpeedBar")))
            driver.execute_script("arguments[0].scrollIntoView(true);", search_bar_locator)
            search_bar_locator.send_keys(mls)

            search_bar_submit = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "ctl01_m_ucSpeedBar_m_lnkGo")))
            driver.execute_script("arguments[0].scrollIntoView(true);", search_bar_submit)
            driver.execute_script("arguments[0].click();", search_bar_submit)

            try:
                logger.info("Waiting for confirmation listing element to be clickable")
                select_listing = driver.find_element(By.XPATH, "//a[contains(text(), 'Listing ID')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", select_listing)
                driver.execute_script("arguments[0].click();", select_listing)
                logger.info(f"{mls} popup confirmed. Submitting search entry.")
            except NoSuchElementException:
                logger.info(f"Submitting {mls} entry")

            click_entry = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, '//td[@class="NoPrint checkboxTableRow d11m0"]//input[@type="checkbox"]')))
            driver.execute_script("arguments[0].scrollIntoView(true);", click_entry)
            driver.execute_script("arguments[0].click();", click_entry)
            logger.info(f"Entry submitted. Clicking {mls} on results page")

            try:
                dropdown_element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, 'm_ucDisplayPicker_m_ddlDisplayFormats')))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", dropdown_element)
                dropdown = Select(dropdown_element)
                dropdown.select_by_visible_text("Agent Full")
                logger.info("Selected 'Agent Full' successfully")

                open_all = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, "//font[@class='print icon' and @title='Open All']")))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", open_all)
                driver.execute_script("arguments[0].click();", open_all)
                logger.info("Selected images page successfully")

                driver.switch_to.window(driver.window_handles[1])
                logger.info("Switched to images page successfully")
            
            except Exception:
                logger.info(f"{mls} listing has no clickable image section")
                break
            
            images_locator = (By.XPATH, "//img[contains(@src, 'https://matrixmedia.brightmls.com')]")
            WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located(images_locator))
            all_imgs = driver.find_elements(*images_locator)
            logger.info("Fetching images")

            if len(all_imgs) <= min_images:
                logger.info('Not enough images')
                return False

            save_dir = f'start_files/static/homes_images/{mls}-pending/'
            image_urls = [img.get_attribute('src') for img in all_imgs]
            current_hash = generate_hash(item, image_urls)

            with get_db_session_pending() as db:
                listing_item = db.query(Mls_homes_temp).filter_by(mls=mls).first()

                if listing_item is None:
                    logger.info(f"{mls} not found in temp database, adding data.")
                    os.makedirs(save_dir, exist_ok=True)
                    save_images(all_imgs, save_dir, max_images)
                    logger.info(f'Converted images to .webp for {mls}')
                    add_listing_to_db(db, mls, item, current_hash, len(all_imgs))
                    logger.info(f"{mls} added to temp database!")
                else:
                    logger.info(f"{mls} found in the temp database. Comparing hashes.")
                    if listing_item.hash != current_hash:
                        logger.info(f"Changes detected for {mls}. Updating temp database.")
                        os.makedirs(save_dir, exist_ok=True)
                        save_images(all_imgs, save_dir, max_images)
                        logger.info(f'Converted images to .webp for {mls}')
                        update_listing_in_db(db, listing_item, item, current_hash, len(all_imgs))
                        logger.info(f"{mls} updated in temp database!")
                    else:
                        logger.info(f"No changes detected for {mls}.")
                        check_and_recreate_images(db, mls, all_imgs, max_images)
            
            return True
                      
        except (WebDriverException, TimeoutException, StaleElementReferenceException):
            logger.error(f"Attempt {attempt + 1} for MLS {mls} failed with error")
            attempt += 1
            time.sleep(delay)

        finally:
            if driver:
                driver.quit()

            logger.info(f'Completed {mls} run')
            return True                        

    logger.error(f"MLS {mls} failed after {max_retries} attempts.")
    return False


async def start_concurrency(max_retries, min_images, delay, timeout, concurrency_limit, max_images, sorted_results: list) -> list:
    semaphore = asyncio.Semaphore(concurrency_limit)
    results = []

    async def download_image_with_semaphore(item):
        async with semaphore:
            for attempt in range(max_retries):
                try:
                    return await asyncio.get_event_loop().run_in_executor(
                        executor, 
                        load_page, 
                        max_images, 
                        min_images, 
                        item, 
                        timeout, 
                        max_retries, 
                        delay
                    )
                except (WebDriverException, TimeoutException, StaleElementReferenceException):
                    logger.error(f"Error processing item {item}. Attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)  
                    else:
                        logger.error(f"Failed to process item {item} after {max_retries} attempts.")
                        raise 

    logger.info("Starting concurrent tasks")
    with ThreadPoolExecutor() as executor:
        tasks = [download_image_with_semaphore(item) for item in sorted_results]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            logger.error("An error occurred during concurrent tasks")
    logger.info("Concurrent tasks completed")
    return results


async def start_task_in_loop(concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay) -> None:
    await export_homes()
    csv_path = "brightscrape/Export_homes.csv"
    while not os.path.exists(csv_path):
        logger.info("Waiting for CSV file to appear...")
        await asyncio.sleep(5) 
    sorted_results = sorted_homes_by_price(max_price)
    logger.info(f"cvs count {len(sorted_results)}")
    init_homes_db()
    init_homes_db_temp() 
    logger.info("Initialized temp database 1.")

    await start_concurrency(max_retries, min_images, delay, timeout, concurrency_limit, max_images, sorted_results)
    clean_up_temp_listings(sorted_results)
    replace_and_cleanup_tables()
    logger.info("Loop task completed successfully")

def start_homes(concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay):
    start_time = time.time()
    logger.info(f"Start Time: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    attempt = 0
    success = False
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        start_task_in_loop(concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay)
    )
    loop.close()
    success = True
    if success:
        clean_and_rename_directories()
        
        for attempt in range(max_retries):
            try:
                if purge_cloudflare_cache():
                    logger.info("Purged cache successfully")
                break 
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} to purge cache failed: {e}")
                time.sleep(delay)
        
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = elapsed_time % 60
        logger.info(f"Elapsed Time: {minutes} minutes {seconds:.2f} seconds")
