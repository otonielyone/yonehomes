import requests
import time

# API URL
API_URL = "http://192.168.200:5000/api/populate_homes_database"

# Parameters
PARAMS = {
    "concurrency_limit": 10,
    "max_retries": 10,
    "delay": 1,
    "timeout": 60,
    "min_images": 2,
    "max_images": 100,
    "max_price": 500000
}

# Retry settings
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds

# Function to perform the API request
def perform_request():
    try:
        response = requests.get(API_URL, params=PARAMS, headers={"Content-Type": "application/json"})
        response.raise_for_status()  # Raise an error for bad responses
        return True
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

# Retry loop
attempt = 0
while attempt < MAX_RETRIES:
    if perform_request():
        print("Request successful")
        exit(0)
    else:
        print(f"Request failed. Attempt {attempt + 1} of {MAX_RETRIES}")
        attempt += 1
        time.sleep(RETRY_DELAY)

print("All attempts failed. Exiting.")
exit(1)
