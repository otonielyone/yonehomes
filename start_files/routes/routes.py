import json

from sqlalchemy import func
from start_files.routes.route_scripts import sorted_csv_by_price, start_task
from start_files.routes.export_scripts import export_results
from start_files.models.users.users import SessionLocal, User, get_listings_from_db
from fastapi import APIRouter, Form, Query, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from flask import jsonify
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


@router.post("/contact")
async def handle_contact_form(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    general_inquiry: str = Form(...)):
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
        """)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"SendGrid response status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending email: {e}")
    logger.info("Contact form submission successful, redirecting user.")
    return RedirectResponse(url="/contact", status_code=303)

@router.get('/api/total_count')
async def get_total_count():
    try:
        # Use SessionLocal to create a database session
        db: Session = SessionLocal()
        total_count = db.query(func.count(User.user_id)).scalar()
        db.close()  # Close the session
        return {"total_count": total_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/get_csv", response_class=JSONResponse, name="export")
async def export_results_endpoint(background_tasks: BackgroundTasks, filter_price: int = 2500):
    logger.info("Starting CSV export task in the background")
    background_tasks.add_task(export_results, filter_price)  # Do not await here
    return JSONResponse(content={"message": "CSV export task started in the background"})

@router.get("/filter_csv_and_count", response_class=JSONResponse, name="filter")
async def sort_csv_endpoint(max_price: int = 2500):
    logger.info("Starting CSV sort task in the background")
    sorted = await sorted_csv_by_price(max_price)
    return f"This sorted list has {len(sorted)} listings."

@router.get("/populate_database", response_model=dict, name="import")
async def get_mls_data(background_tasks: BackgroundTasks, concurrency_limit: int = 10,  max_retries: int = 20, delay: int= 1, timeout: int = 300, max_images: int = 50, max_price: int = 2500):
    logger.info("Starting MLS data gathering task")
    background_tasks.add_task(start_task, concurrency_limit, timeout, max_images, max_price, max_retries, delay)
    return JSONResponse(content={"message": "MLS data gathering task started in the background"})
    
@router.get("/", response_class=HTMLResponse, name="home")
async def read_root(request: Request):
    logger.info("Rendering home page")
    templates = request.app.state.templates
    return templates.TemplateResponse("home.html", {"request": request})

@router.get('/api/listings')
async def api_listings():
    try:
        db = SessionLocal()
        # Get all listings data from the database
        listings_data = get_listings_from_db(db)
        db.close()
        # Return the data wrapped in a dictionary with the key "listings"
        return {"listings": listings_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
