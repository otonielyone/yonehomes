import os
import requests

def purge_cloudflare_cache():
    response = requests.post(
        f'https://api.cloudflare.com/client/v4/zones/{os.getenv("CLOUDFLARE_ZONE")}/purge_cache',
        headers={
            'Authorization': f'Bearer {os.getenv("CLOUDFLARE_API_TOKEN")}',
            'Content-Type': 'application/json',
        },
        json={'purge_everything': True}
    )
    return response.json()

def set_cache_headers():
    # Your logic to set cache headers
    os.system('find /var/www/html/fastapi_project/start_files/static/ -type f \\( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" -o -iname "*.webp" \\) -exec touch -d "tomorrow" {} \\;')

if __name__ == "__main__":
    # Set the cache headers for all images
    set_cache_headers()
    
    # Purge the Cloudflare cache
    result = purge_cloudflare_cache()
    print(result)
