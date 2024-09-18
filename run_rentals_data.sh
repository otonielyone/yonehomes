#!/bin/bash

# API URL
API_URL="https://yonehomes.com/api/populate_rentals_database"

# Parameters
PARAMS="concurrency_limit=10&max_retries=10&delay=1&timeout=60&min_images=2&max_images=100&max_price=3000"

# Retry settings
MAX_RETRIES=5
RETRY_DELAY=10 # seconds

# Function to perform the API request
perform_request() {
    curl -X GET "$API_URL?$PARAMS" -H "Content-Type: application/json"
}

# Retry loop
attempt=0
while [ $attempt -lt $MAX_RETRIES ]; do
    perform_request
    if [ $? -eq 0 ]; then
        echo "Request successful"
        exit 0
    else
        echo "Request failed. Attempt $((attempt + 1)) of $MAX_RETRIES"
        attempt=$((attempt + 1))
        sleep $RETRY_DELAY
    fi
done

echo "All attempts failed. Exiting."
exit 1
