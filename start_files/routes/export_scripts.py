from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from fastapi import APIRouter, HTTPException
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
from selenium import webdriver
import asyncio
import logging
import shutil
import csv
import re
import os


router = APIRouter()

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


async def async_setup_options() -> webdriver.Chrome:
    logger.info("Setting up async driver")
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
    service = ChromeService(executable_path='/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    logger.info("Chrome options setup complete")
    return driver


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


##GET EXCCEL
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
    
    except TimeoutException as e:
        logger.error(f"TimeoutException occurred navigating to excel. Refreshing the page and retrying.")
        driver.refresh()
        await navigate_to_search_page(driver, timeout)

async def export_results(max_price):
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
        logger.info("Export selected from dropdown")

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
 
    except Exception:
        logger.error(f"Error during export results")
        raise HTTPException(status_code=500, detail="Error during export results")
    
    finally:
        logger.info('Done fetching csv')
        if 'driver' in locals() or driver is not None:
            driver.quit()
    
    try:
        logger.info("Sorting and filtering cvs file..")
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
                bedrooms = row[79]
                bath = row[80]

                if (max_price is None or price < max_price) and state == 'VA':
                    all_data.append((price, mls, street_unit, status, list_date, city, state, zip_code,
                                    listing_office, listing_office_number, listing_agent, listing_agent_number,
                                    listing_agent_email, agent_remarks, public_remarks, bedrooms, bath))
        logger.info(f'Filted and sorted csv: total {len(all_data)}')
        return sorted(all_data, key=lambda x: x[0])

    except Exception:
        logger.error(f"Error during sorting and filtering results")
        raise HTTPException(status_code=500, detail="Error during sorting and filtering resultd")