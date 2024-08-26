import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from start_files.config import get_templates, flash, get_flashed_messages

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()
load_dotenv()

@router.get("/", response_class=HTMLResponse, name="home")
async def read_root(request: Request):
    templates = get_templates()
    flash(request, "Welcome to Yone Homes!", "success")
    return templates.TemplateResponse("home.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/rentals", response_class=HTMLResponse, name="rentals")
async def rentals(request: Request):
    templates = get_templates()
    return templates.TemplateResponse("rentals.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/buying", response_class=HTMLResponse, name="buying")
async def buying(request: Request):
    templates = get_templates()
    return templates.TemplateResponse("buying.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/resources", response_class=HTMLResponse, name="resources")
async def resources(request: Request):
    templates = get_templates()
    return templates.TemplateResponse("resources.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

def send_email(subject: str, message: str, sender_email: str, recipient_email: str, password: str):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    logger.info(f"Sending email to {recipient_email}")

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        logger.info("Email sent successfully!")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while sending the email.")

@router.get("/contact", response_class=HTMLResponse, name="contact")
async def contact(request: Request):
    templates = get_templates()
    return templates.TemplateResponse("contact.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.post("/contact", response_class=HTMLResponse, name="submit_contact")
async def submit_contact(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    general_inquiry: str = Form(...)
):
    logger.info("Contact form submitted")

    templates = get_templates()

    subject = "New Contact Form Submission"
    message = f"""
    You have received a new message from your contact form.

    First Name: {first_name}
    Last Name: {last_name}
    Email: {email}
    Phone: {phone}
    General Inquiry:
    {general_inquiry}
    """

    sender_email = os.getenv('SENDER')
    recipient_email = os.getenv('RECIPIENT')
    password = os.getenv('PASSWORD')

    logger.info(f"Sender Email: {sender_email}")
    logger.info(f"Recipient Email: {recipient_email}")
    logger.info(f"Password: {password}")

    print("SENDER:", os.getenv('SENDER'))
    print("RECIPIENT:", os.getenv('RECIPIENT'))
    print("PASSWORD:", os.getenv('PASSWORD'))

    try:
        send_email(subject, message, sender_email, recipient_email, password)
        flash(request, "Thank you for your message. We will get back to you shortly.", "success")
        return templates.TemplateResponse("contact.html", {"request": request, "flashed_messages": get_flashed_messages(request)})
    except HTTPException as e:
        logger.error(f"Exception: {e}")
        flash(request, "There was an error sending your message. Please try again later.", "error")
        return templates.TemplateResponse("contact.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

def create_app() -> FastAPI:
    app = FastAPI()

    app.mount("/static", StaticFiles(directory="start_files/static"), name="static")

    templates = get_templates()
    app.state.templates = templates

    # Include routes from the router
    app.include_router(router)

    return app
