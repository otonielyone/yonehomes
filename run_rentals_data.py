import os
import requests
import time
import logging
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define the directory and virtual environment
project_directory = "/var/www/html/test_site"
venv_python = os.path.join(project_directory, ".venv", "bin", "python")

# Change to the project directory
os.chdir(project_directory)
logging.info(f"Changed working directory to: {os.getcwd()}")

# API URL
API_URL = "http://192.168.0.201:5000/api/populate_rentals_database"

# Parameters
PARAMS = {
    "concurrency_limit": 10,
    "max_retries": 10,
    "delay": 1,
    "timeout": 60,
    "min_images": 2,
    "max_images": 100,
    "max_price": 3000,
}

# Retry settings
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds

def perform_request():
    try:
        response = requests.get(API_URL, params=PARAMS, timeout=60)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()  # Return the JSON response
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None

# Retry loop
for attempt in range(1, MAX_RETRIES + 1):
    result = perform_request()
    if result is not None:
        logging.info("Request successful")
        break
    else:
        logging.info(f"Request failed. Attempt {attempt} of {MAX_RETRIES}")
        time.sleep(RETRY_DELAY)
else:
    logging.error("All attempts failed. Exiting.")
