#!/bin/bash

# Set the cache headers for all images inside /static and its subdirectories
find /var/www/html/yonehomes/start_files/static/ -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" -o -iname "*.webp" \) -exec touch -d "tomorrow" {} \;

