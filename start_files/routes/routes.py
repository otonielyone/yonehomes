import shutil

import httpx
from start_files.models.mls.rentals_db_section import get_rentals_from_db
from start_files.models.mls.homes_db_section import get_homes_from_db
from start_files.routes.rentals_scripts import sorted_rentals_by_price, start_rentals
from start_files.routes.homes_scripts import sorted_homes_by_price, start_homes
from fastapi import APIRouter, Form, Path, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from sqlalchemy import func
from typing import List
import logging
import os


router = APIRouter()

load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT = os.getenv("RECIPIENT")
SENDER = os.getenv("SENDER")

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

    
@router.get("/", response_class=HTMLResponse, name="home")
async def read_root(request: Request):
    logger.info("Rendering home page")
    templates = request.app.state.templates
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/rentals", response_class=HTMLResponse, name="rentals")
async def rentals(request: Request):
    logger.info("Rendering rentals page")
    templates = request.app.state.templates
    return templates.TemplateResponse("rentals.html", {"request": request})

@router.get("/buying", response_class=HTMLResponse, name="buying")
async def buying(request: Request):
    logger.info("Rendering buying page")
    templates = request.app.state.templates
    return templates.TemplateResponse("buying.html", {"request": request})

@router.get("/resources", response_class=HTMLResponse, name="resources")
async def resources(request: Request):
    logger.info("Rendering resources page")
    templates = request.app.state.templates
    return templates.TemplateResponse("resources.html", {"request": request})

@router.get("/contact", response_class=HTMLResponse, name="contact")
async def contact(request: Request):
    logger.info("Rendering contact page")
    templates = request.app.state.templates
    return templates.TemplateResponse("contact.html", {"request": request})

@router.post("/contact")
async def handle_contact_form(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    general_inquiry: str = Form(...)
):
    logger.info(f"Received contact form submission from {email}")

    message = Mail(
        from_email=SENDER,
        to_emails=RECIPIENT,
        subject='New Contact Form Submission',
        html_content=f"""
        <p>First Name: {first_name}</p>
        <p>Last Name: {last_name}</p>
        <p>Email: {email}</p>
        <p>Phone: {phone}</p>
        <p>General Inquiry: {general_inquiry}</p>
        """
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"SendGrid response status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Error sending email")

    logger.info("Contact form submission successful, redirecting user.")
    return RedirectResponse(url="/contact", status_code=303)


@router.get("/api/filter_rentals_export", response_class=JSONResponse, name="filter")
async def sort_rental_endpoint(max_price: int = 2500):
    logger.info("Starting CSV sort task in the background")
    sorted = sorted_rentals_by_price(max_price)
    return f"This sorted list has {len(sorted)} listings."

@router.get("/api/populate_rentals_database", response_model=dict, name="import")
async def get_rental_data(background_tasks: BackgroundTasks, concurrency_limit: int = 10,  max_retries: int = 20, delay: int= 1, timeout: int = 300, min_images: int = 2, max_images: int = 50, max_price: int =3000):
    logger.info("Starting MLS rentals gathering task")
    background_tasks.add_task(start_rentals, concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay)
    return JSONResponse(content={"message": "MLS data gathering rental task started in the background"})

@router.get('/api/view_rentals_database')
async def api_rentals():
        listings_data = get_rentals_from_db()
        return {"rentals": listings_data}
    

@router.get('/api/rentals_database_count')
async def get_total_count():
    try:
        listings_data = get_rentals_from_db()
        if listings_data is None:
            raise ValueError("No data returned from the database")
        return {"rentals Count": len(listings_data)}
    except Exception as e:
        print(f"Error in get_total_count: {e}")  # Log the error
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/filter_homes_export", response_class=JSONResponse, name="filter")
async def sort_homes_endpoint(max_price: int = 2500):
    logger.info("Starting CSV sort task in the background")
    sorted = sorted_homes_by_price(max_price)
    return f"This sorted list has {len(sorted)} listings."

@router.get("/api/populate_homes_database", response_model=dict, name="import")
async def get_home_data(background_tasks: BackgroundTasks, concurrency_limit: int = 10,  max_retries: int = 20, delay: int= 1, timeout: int = 300, min_images: int = 2, max_images: int = 100, max_price: int = 500000):
    logger.info("Starting MLS homes gathering task")
    background_tasks.add_task(start_homes, concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay)
    return JSONResponse(content={"message": "MLS data gathering home task started in the background"})

@router.get('/api/view_homes_database')
async def api_homes():
    listings_data = get_homes_from_db()
    return {"homes": listings_data}
    
@router.get('/api/homes_database_count')
async def get_total_count():
    try:
        listings_data = get_homes_from_db()
        return {"homes count":len(listings_data)}
    except Exception:
        raise HTTPException(status_code=500)
    
@router.get("/home_search")
async def home_search(request: Request):
    external_url = "https://otonielyone.unitedrealestatewashingtondc.com/index.htm"
    async with httpx.AsyncClient() as client:
        response = await client.get(external_url)
        return StreamingResponse(
            content=response.aiter_raw(),
            headers=dict(response.headers),
            status_code=response.status_code
        )
    
#def install_backups():
#    db_path = "brightscrape/brightmls_rentals.db.bak"
#    new_db_name = db_path[:-4]
#
#    if os.path.exists(db_path):
#        os.rename(db_path, new_db_name)
#
#    base_dir = '/var/www/html/fastapi_project/start_files/static/rentals_images/'
#
#    for item in os.listdir(base_dir):
#        item_path = os.path.join(base_dir, item)
#
#        if os.path.isdir(item_path) and item.endswith('.bak'):
#            new_name = item[:-4]
#            new_path = os.path.join(base_dir, new_name)
#            try:
#                shutil.move(item_path, new_path)
#                print(f"Renamed directory: {item_path} to {new_path}")
#            except Exception:
#                print(f"Error renaming directory {item_path} to {new_path}")
#        
#        elif os.path.isdir(item_path):
#            try:
#                shutil.rmtree(item_path)
#                print(f"Removed non-backup directory: {item_path}")
#            except Exception:
#                print(f"Error removing directory {item_path}")
#install_backups()
