import csv
import os
import re
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment variables
BRIGHTMLS_USERNAME = os.getenv("BRIGHTMLS")
BRIGHTMLS_PASSWORD = os.getenv("PASSWORD")

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # Corrected format string
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def setup_options() -> webdriver.Chrome:
    logger.info("Setting up driver")
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    try:
        service = ChromeService(executable_path='/usr/lib/chromium-browser/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {e}")
        raise

def login(driver: webdriver.Chrome, timeout: int, username: str, password: str):
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


async def preprocess_price(price_str: str) -> float:
    match = re.search(r'\d+', price_str.replace(',', ''))
    if match:
        return float(match.group())
    return float('inf')

async def sorted_csv_by_price(max_price: float = None) -> list:
    logger.info("About to Begin sorting csv")
    csv_path = "/var/www/html/fastapi_project/brightscrape/Standard_Export.csv"
    all_data = []
    try:
        with open(csv_path, mode='r') as data:
            data_content = csv.reader(data, delimiter=',')
            next(data_content, None)  # Skip header row
            for row in data_content:
                price = await preprocess_price(row[6])
                if (max_price is None or price < max_price) and row[23] == 'VA':
                    all_data.append((price, row[0], row[1], row[3], row[11], row[22], row[23], row[24], 
                                     row[37], row[38], row[39], row[40], row[41], row[42], row[44]))
    except Exception as e:
        logger.error(f"CSV processing failed: {e}")
    logger.debug("Sorted done")
    return sorted(all_data, key=lambda x: x[0])

def download_images_for_item(item, timeout: int, max_images: int) -> list:
    logger.info(f"About to Begin gathering images for MLS {item[1]}")
    mls = item[1]
    image_link_full = []
    driver = setup_options()
    try:
        login(driver, timeout, BRIGHTMLS_USERNAME, BRIGHTMLS_PASSWORD)
        logger.info(f"Logged in now to gather the images")

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
        driver.save_screenshot('debug_screenshot.png')

        formula_span = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, "//span[text()='Click to Show Photos']")))
        driver.save_screenshot('debug_screenshot2.png')
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", formula_span)
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Click to Show Photos']")))
        driver.execute_script("arguments[0].click();", formula_span)
        logger.info(f" Clicking image section for {item[1]}")
    
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
                
        image_link_full.append([mls, all_links])
    except Exception as e:
        logger.error(f"Exception: Unexpected error for MLS {mls}: {e}")
    return {name: links for name, links in image_link_full}

    
async def download_images(timeout: int, sorted_results: list) -> list:
    max_images = 10
    logger.info("About to Begin concurrency")
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [loop.run_in_executor(executor, download_images_for_item, item, timeout, max_images) for item in sorted_results]
        mls_links_dict = await asyncio.gather(*tasks)
        try:
            for item in sorted_results:
                name = item[1]
                images = mls_links_dict.get(name, [])
                
            print({
                'mls': name,
                'address': f"{item[2]}, {item[5]}, {item[6]} {item[7]}",
                'price': item[0],
                'description': item[14],
                'availability': item[3],
                'image_list': images
            })

        finally:
            logger.debug(f"Database has been populated")


async def gather_images_and_mls_data():
    timeout = 120
    max_price = 1000
    sorted_results = await sorted_csv_by_price(max_price)
    return await download_images(timeout, sorted_results)

async def get_mls_data():
    try:
        data = await gather_images_and_mls_data()
        print(data)
    except Exception as e:
        logger.error(f"Failed to gather MLS data: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(get_mls_data())
