import shutil
import time
import os
import logging
import asyncio
import sys
from pydantic import BaseModel
from selenium.webdriver.support import expected_conditions as EC
from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from sendgrid import SendGridAPIClient
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, WebDriverException
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from typing import Optional, List
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys


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

async def export_results(driver, timeout):
    logger.info("Starting export_results function")
    await asyncio.sleep(5)

    try:
        logger.debug("Waiting for 'Check All Results Entries' link to be clickable")
        element_present = EC.element_to_be_clickable((By.ID, "m_lnkCheckAllLink"))
        WebDriverWait(driver, timeout).until(element_present)
        all = driver.find_element(by=By.ID, value="m_lnkCheckAllLink")
        driver.execute_script("arguments[0].click();", all)
        logger.info("'Check All Results Entries' link clicked successfully")

        logger.debug("Waiting for 'Submit Export' button to be clickable")
        element_present = EC.element_to_be_clickable((By.ID, "m_lbExport"))
        WebDriverWait(driver, timeout).until(element_present)
        pre_export = driver.find_element(by=By.ID, value="m_lbExport")
        driver.execute_script("arguments[0].click();", pre_export)
        logger.info("'Submit Export' button clicked successfully")

        await asyncio.sleep(2)

        logger.debug("Waiting for dropdown to be clickable")
        select_element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//select[@id='m_ddExport']"))
        )
        driver.execute_script("arguments[0].click();", select_element)
        select_element.send_keys("s")
        select_element.send_keys(Keys.ENTER)
        logger.info("Standard Export selected from dropdown")

        logger.debug("Waiting for 'Export' button to be clickable")
        element_present = EC.element_to_be_clickable((By.ID, "m_btnExport"))
        WebDriverWait(driver, timeout).until(element_present)
        export = driver.find_element(by=By.ID, value="m_btnExport")
        driver.execute_script("arguments[0].click();", export)
        logger.info("'Export' button clicked successfully")

        logger.debug("Waiting for file to download")
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
    
async def get_csv():
    logger.info("Starting get_csv function")
    driver = None  # Initialize driver as None
    try:
        timeout = 100
        driver = await setup_options()
        await login(driver, timeout, BRIGHTMLS_USERNAME, BRIGHTMLS_PASSWORD)
        await navigate_to_search_page(driver, timeout)
        await export_results(driver, timeout)
    
    except Exception as e:
        logger.error(f"Failed to gather MLS data: {e}")
        raise HTTPException(status_code=500, detail="Failed to gather MLS data")
    
    finally:
        if driver:
            logger.info("Quitting driver")
            driver.quit()
        
    

if __name__ == "__main__":
    asyncio.run(get_csv())
