#!/bin/bash

API_URL="https://yonehomes.com/api/populate_rental_database"

curl -X GET "$API_URL?concurrency_limit=10&max_retries=20&delay=1&timeout=300&min_images=2&max_images=50&max_price=3000" -H "Content-Type: application/json"
