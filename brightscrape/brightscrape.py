import asyncio
import csv
import re
import shutil
import sys
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import urllib.request
from webdriver_manager.chrome import ChromeDriverManager


async def setup_options():
    options = Options()
#    options.add_argument('--headless')  # Run headless Chrome
    options.add_argument('--no-sandbox')  # Disable sandboxing for containerized environments
    options.add_argument('--disable-dev-shm-usage')  # Avoid /dev/shm issues
    options.add_argument('--disable-gpu')  # Disable GPU acceleration (optional, but can help in some cases)
    chrome_service = Service('/usr/lib/chromium-browser/chromedriver')  # Path to chromedriver
    driver = webdriver.Chrome(service=chrome_service, options=options)
    return driver


async def login(driver, timeout, add_username, add_password):
    #Go to page - will redirect to login
    driver.get("https://matrix.brightmls.com/Matrix/Search/ResidentialLease/ResidentialLease")

    #Find username
    try:
        element_present = EC.element_to_be_clickable((By.NAME,"username"))
        WebDriverWait(driver, timeout).until(element_present)

    except TimeoutException:
        print("Timed out waiting for Login Page to Load")
        sys.exit()

    #Set Usernamee
    field_username = driver.find_element(by=By.NAME, value="username")
    field_username.send_keys(f"{add_username}")
    #Set Password
    field_password = driver.find_element(by=By.ID, value="password")
    field_password.send_keys(f"{add_password}")
    #Submit
    button = driver.find_element(by=By.CSS_SELECTOR, value=".css-yck31-root-root-root")
    button.click()


async def sorted_csv_by_price(max_price=None):
    csv_path = "/var/www/html/fastapi_project/brightscrape/Standard_Export.csv"

    all_data = []

    async def preprocess_price(price_str):
        match = re.search(r'\d+', price_str.replace(',', ''))
        if match:
            return float(match.group())
        return float('inf')  

    # Open the CSV file and process its content
    with open(csv_path, mode='r') as data:
        data_content = csv.reader(data, delimiter=',')

        # Skip header row
        next(data_content, None)

        # Read each row of data
        for row in data_content:
            # Extract data from the row
            mls = row[0]                            # MLS number (index 0)
            street_unit = row[1]                    # Street/unit (index 1)
            status = row[3]                         # Status (index 3)
            price = await preprocess_price(row[6])  # Price (index 6)
            list_date = row[11]                     # Listing date (index 11)
            city = row[22]                          # City (index 22)
            state = row[23]                         # State (index 23)
            zip_code = row[24]                      # Zip code (index 24)
            listing_office = row[37]                # Listing office (index 37)
            listing_office_number = row[38]         # Listing office number (index 38)
            listing_agent = row[39]                 # Listing agent (index 39)
            listing_agent_number = row[40]          # Listing agent number (index 40)
            listing_agent_email = row[41]           # Listing agent email (index 41)
            agent_remarks = row[42]                 # Agent remarks (index 42)
            public_remarks = row[44]                # Public remarks (index 44)

            if (max_price is None or price < max_price) and state == 'VA':
                # Append the tuple of data to all_data
                all_data.append((price, mls, street_unit, status, list_date, city, state, zip_code,
                                 listing_office, listing_office_number, listing_agent, listing_agent_number,
                                 listing_agent_email, agent_remarks, public_remarks))

    # Sort all_data by price (index 0 of each tuple)
    all_data_sorted = sorted(all_data, key=lambda x: x[0])

    return all_data_sorted


async def download_images(driver, timeout, sorted_results):
    sorted_mls = [item[1] for item in sorted(sorted_results)]
    listing_count = len(sorted_mls)

    image_link_full = []
    for count in range(listing_count):
        mls = sorted_mls[count]

        
        try:

                # Wait for search bar to be present
                search_bar_locator = (By.NAME, "ctl01$m_ucSpeedBar$m_tbSpeedBar")
                WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(search_bar_locator))

                # Interact with search bar
                search_mls = driver.find_element(*search_bar_locator)
                search_mls.clear()
                search_mls.send_keys(mls)

                # Wait for Go button to be present
                go_button_locator = (By.ID, "ctl01_m_ucSpeedBar_m_lnkGo")
                WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(go_button_locator))

                # Click Go button
                go_button = driver.find_element(*go_button_locator)
                go_button.click()

                # Wait for MLS details link to be present
                mls_details_locator = (By.XPATH, '//td[@class="d25m6"]//span[@class="d25m1"]')
                WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(mls_details_locator))

                # Click on MLS record
                mls_record = driver.find_element(*mls_details_locator)
                mls_record.click()

                # Wait for MLS page elements to load
                Find_click_to_open = (By.XPATH, '//*[@class="d76m22"]//span[@class="formula"]')
                WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(Find_click_to_open))

                # Click to open images
                open_images = driver.find_element(*Find_click_to_open)
                driver.execute_script("arguments[0].scrollIntoView(true);", open_images)
                open_images.click()

                # Wait for images to load
                images_locator = (By.XPATH, '//font[@class="IV_Single"]//img[@class="IV_Image"]')
                WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located(images_locator))

                # Get all image elements
                all_imgs = driver.find_elements(*images_locator)

                # Gather images
                all_links = []
                for i, tag in enumerate(all_imgs[:max_images], start=1):  # Limit to 5 images
                    try:
                        image_link = tag.get_attribute('src')
                        all_links.append(image_link)
                    except Exception as e:
                        print(f"Failed to gather image url: {i} for {mls}: {e}")
                
                if len(all_links) == 0:
                    print(f"Error: {mls} has no images.")
                    if mls in sorted_mls:
                        sorted_mls.remove(mls)
                else:
                    print(f"Completed image extractions for MLS {mls}, found {len(all_imgs)} images.")
                await asyncio.sleep(1)
                image_link_full.append([mls,all_links])

        except Exception as e:
            print(f"Exception: Unexpected error for MLS {mls}: {e}")
            if mls in sorted_mls:
                    sorted_mls.remove(mls)

    return image_link_full    
                
async def pass_on_list(sorted_results):
    #mls, address, price, availibity, decription
    pass_on_list = [
        [item[1], f"{item[2]}, {item[5]}, {item[6]} {item[7]}", item[0], item[14], item[3]]
        for item in sorted_results
    ]
    flip = pass_on_list[::-1]
    return flip

async def gather_images_and_mls_data(timeout, max_price):
        driver = await setup_options()
       
        await login(driver, timeout, add_username, add_password)
        
        sorted_results = await sorted_csv_by_price(max_price)
        mls_list = await pass_on_list(sorted_results)
        print(f"There are {len(mls_list)} listings in this list")

        results = await download_images(driver, timeout, sorted_results)
        print(results)
        
        await asyncio.sleep(1)  

if __name__ == "__main__":
    max_images=10
    timeout = 100
    max_price=1000
    add_username = "otonielyone"
    add_password = "Exotica12345@"
    asyncio.run(gather_images_and_mls_data(timeout, max_price))