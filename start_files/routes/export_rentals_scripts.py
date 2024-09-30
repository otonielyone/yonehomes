from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
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
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    service = ChromeService(executable_path='/usr/bin/chromedriver')
    max_retries = 5

    for attempt in range(max_retries):
        try:
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except WebDriverException:
            logger.error(f"Driver retrying.. {attempt + 1}")
            if attempt == max_retries - 1:
                raise
            asyncio.sleep(1)

    raise RuntimeError("Failed to start Chrome after multiple attempts")



async def async_login(driver: webdriver.Chrome, timeout: int, username: str, password: str):
    logger.info("About to Begin Login")
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            driver.get("https://matrix.brightmls.com/Matrix/Search/ResidentialLease/ResidentialLease")
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

            logger.info("Login successful")
            return 

        except Exception as e:
            logger.error(f"Login failed on attempt {attempt}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {1} seconds...")
                await asyncio.sleep(1)
            else:
                logger.error("Max retries reached. Login failed.")
                raise
            

async def navigate_to_search_page(driver, timeout):
    logger.info("Navigating to search page")
    max_retries = 5
    for attempt in range(1, max_retries + 1):
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
            return  # Exit the function on success

        except TimeoutException:
            logger.error(f"TimeoutException occurred on attempt {attempt}.")
            if attempt < max_retries:
                logger.info(f"Retrying in {1} seconds...")
                driver.refresh()
                await asyncio.sleep(1)
            else:
                logger.error("Max retries reached. Navigation failed.")
                raise
        except Exception as e:
            logger.error(f"An error occurred on attempt {attempt}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {1} seconds...")
                await asyncio.sleep(1)
            else:
                logger.error("Max retries reached. Navigation failed.")
                raise




async def export_rentals():
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
        csv_path2 = "brightscrape/Export_rentals.csv"

        while not os.path.exists(csv_path1):
            await asyncio.sleep(1)
        logger.info(f"File downloaded: {csv_path1}")
        
        shutil.move(csv_path1, csv_path2)
        logger.info(f"File moved from {csv_path1} to {csv_path2}")
 
    finally:
        logger.info('Done fetching csv')
        if 'driver' in locals() or driver is not None:
            driver.quit()
    
