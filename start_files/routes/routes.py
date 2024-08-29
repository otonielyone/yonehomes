from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
import os
import logging

from start_files.config import flash, get_flashed_messages

router = APIRouter()

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Add console handler to output logs to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Load environment variables from .env file
load_dotenv()

# Retrieve credentials from environment variables
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT = os.getenv("RECIPIENT")
SENDER = os.getenv("SENDER")

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
    
    # Construct the email content
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
    
    # Send the email
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"SendGrid response status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending email: {e}")

    # Flash a message and redirect
    flash(request, "Your message has been sent successfully!", "success")
    logger.info("Contact form submission successful, redirecting user.")
    return RedirectResponse(url="/contact", status_code=303)

@router.get("/", response_class=HTMLResponse, name="home")
async def read_root(request: Request):
    logger.info("Rendering home page")
    templates = request.app.state.templates
    flash(request, "Welcome to Yone Homes!", "success")
    return templates.TemplateResponse("home.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/rentals", response_class=HTMLResponse, name="rentals")
async def rentals(request: Request):
    logger.info("Rendering rentals page")
    templates = request.app.state.templates
    return templates.TemplateResponse("rentals.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/buying", response_class=HTMLResponse, name="buying")
async def buying(request: Request):
    logger.info("Rendering buying page")
    templates = request.app.state.templates
    return templates.TemplateResponse("buying.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/resources", response_class=HTMLResponse, name="resources")
async def resources(request: Request):
    logger.info("Rendering resources page")
    templates = request.app.state.templates
    return templates.TemplateResponse("resources.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/contact", response_class=HTMLResponse, name="contact")
async def contact(request: Request):
    logger.info("Rendering contact page")
    templates = request.app.state.templates
    return templates.TemplateResponse("contact.html", {"request": request, "flashed_messages": get_flashed_messages(request)})
