from start_files.models.mls.rentals import rentals_sessionLocal2, rentals_engine, get_rentals_from_db
from start_files.models.mls.homes import homes_sessionLocal2, homes_engine, get_homes_from_db
from start_files.routes.rentals_scripts import sorted_rentals_by_price, start_rentals
from fastapi import APIRouter, Form, Path, Request, HTTPException, BackgroundTasks
from start_files.routes.homes_scripts import sorted_homes_by_price, start_homes
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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


@router.get("/api/filter_rental_export", response_class=JSONResponse, name="filter")
async def sort_rental_endpoint(max_price: int = 2500):
    logger.info("Starting CSV sort task in the background")
    sorted = sorted_rentals_by_price(max_price)
    return f"This sorted list has {len(sorted)} listings."

@router.get("/api/populate_rental_database", response_model=dict, name="import")
async def get_rental_data(background_tasks: BackgroundTasks, concurrency_limit: int = 10,  max_retries: int = 20, delay: int= 1, timeout: int = 300, min_images: int = 2, max_images: int = 50, max_price: int =3000):
    logger.info("Starting MLS data gathering task")
    background_tasks.add_task(start_rentals, concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay)
    return JSONResponse(content={"message": "MLS data gathering task started in the background"})

@router.get('/api/view_rental_database')
async def api_rentals():
    try:
        listings_data = get_rentals_from_db()
        return {"rentals":listings_data}
    except Exception:
        raise HTTPException(status_code=500)

@router.get('/api/rental_database_count')
async def get_total_count():
    try:
        listings_data = get_rentals_from_db()
        return {"rentals Count":len(listings_data)}
    except Exception:
        raise HTTPException(status_code=500)

@router.get("/api/filter_homes_export", response_class=JSONResponse, name="filter")
async def sort_homes_endpoint(max_price: int = 2500):
    logger.info("Starting CSV sort task in the background")
    sorted = sorted_homes_by_price(max_price)
    return f"This sorted list has {len(sorted)} listings."

@router.get("/api/populate_homes_database", response_model=dict, name="import")
async def get_home_data(background_tasks: BackgroundTasks, concurrency_limit: int = 10,  max_retries: int = 20, delay: int= 1, timeout: int = 300, min_images: int = 2, max_images: int = 50, max_price: int = 2500):
    logger.info("Starting MLS data gathering task")
    background_tasks.add_task(start_homes, concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay)
    return JSONResponse(content={"message": "MLS data gathering task started in the background"})

@router.get('/api/view_homes_database')
async def api_homes():
    try:
        listings_data = get_homes_from_db()
        return {"HOMES":listings_data}
    except Exception:
        raise HTTPException(status_code=500)

@router.get('/api/homes_database_count')
async def get_total_count():
    try:
        listings_data = get_homes_from_db()
        return {"homes count":len(listings_data)}
    except Exception:
        raise HTTPException(status_code=500)
    
@router.get("/api/getImages/{mls}", response_model=List[str])
async def get_images(mls: str = Path(...)):
    directory_path = f'/var/www/html/fastapi_project/start_files/static/images/{mls}'

    if not os.path.exists(directory_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        files = os.listdir(directory_path)
        image_files = [f"static/images/{mls}/{file}" for file in files if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        return image_files
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to read directory")
