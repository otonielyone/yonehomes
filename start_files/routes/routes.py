from start_files.models.mls.leads_db_section import leads_sessionLocal, Mls_leads, get_notes_from_db, save_notes_from_db, delete_notes_from_db, NoteResponse, save_customer_info_in_db, CRM
from start_files.models.mls.analytics import Analytics, analytics_sessionLocal, get_analytics_from_db, get_sub_table_from_db, SubTable
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest
from google.analytics.data_v1beta import BetaAnalyticsDataClient, RunReportRequest
from fastapi import APIRouter, Form, Request, HTTPException, BackgroundTasks
from start_files.models.mls.rentals_db_section import get_rentals_from_db
from start_files.models.mls.homes_db_section import get_homes_from_db
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from start_files.routes.rentals_scripts import start_rentals
from start_files.routes.leads_scripts import start_leads
from start_files.routes.homes_scripts import start_homes
from fastapi.responses import HTMLResponse
from google.oauth2 import service_account
from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from typing import Any, Dict, List
from fastapi import HTTPException, Depends
from sqlalchemy import desc, func
from collections import Counter
from dotenv import load_dotenv
from pydantic import BaseModel
import logging
import httpx
import os

router = APIRouter()

load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT = os.getenv("RECIPIENT")
SENDER = os.getenv("SENDER")
MAILJET_API = os.getenv("MAILJET_API")
MAILJET_SECRET = os.getenv("MAILJET_SECRET")
GA_VIEW_ID = os.getenv("GA_VIEW_ID")
ALLOWED_IPS = os.getenv("ALLOWED_IPS")

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


########################################
############ GENERAL ROTUES ############
########################################
@router.get("/", response_class=HTMLResponse, name="home")
async def read_root(request: Request):
    logger.info("Rendering home page")
    templates = request.app.state.templates
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/idx")
async def home_search(request: Request):
    external_url = "https://otonielyone.unitedrealestatewashingtondc.com/index.htm"
    async with httpx.AsyncClient() as client:
        response = await client.get(external_url)
        return StreamingResponse(
            content=response.aiter_raw(),
            headers=dict(response.headers),
            status_code=response.status_code
        )

@router.get("/error", response_class=HTMLResponse)
async def error_page(request: Request):
    return """
    <html>
        <head>
            <style>
                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-family: Arial, sans-serif;
                }
                h1 {
                    text-align: center;
                }
                p {
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div>
                <h1>Sorry, Access Denied</h1>
                <p>You do not have permission to access this page.</p>
            </div>
        </body>
    </html>
    """

@router.get("/buying", response_class=HTMLResponse, name="buying")
async def buying(request: Request):
    logger.info("Rendering buying page")
    templates = request.app.state.templates
    return templates.TemplateResponse("buying.html", {"request": request})

@router.get("/rentals", response_class=HTMLResponse, name="rentals")
async def rentals(request: Request):
    logger.info("Rendering rentals page")
    templates = request.app.state.templates
    return templates.TemplateResponse("rentals.html", {"request": request})

@router.get("/leads", response_class=HTMLResponse, name="leads")
async def view_leads(request: Request):
    db = leads_sessionLocal()
    
    # Fetch leads from the Mls_leads table
    leads_db = db.query(Mls_leads).all()
    leads = []
    for lead in leads_db:
        leads.append({
            'MLS': lead.mls,
            'Status': lead.status,
            'Sale_Amount': lead.sale_amt,
            'List_Price': lead.list_price,
            'Owner_Phone': lead.owner_phone,
            'Owner_Name': lead.owner_name,
            'Owner_Names': lead.owner_names,
            'Owner_Last_Name': lead.owner_last_name,
            'Owner_First_Name': lead.owner_first_name,
            'Owner2_Last_Name': lead.owner2_last_name,
            'Owner_Address': f"{lead.owner_address} {lead.owner_city_state or ''}, {lead.owner_zip_code or ''}",
            'Owner_Occupied': 'Yes' if lead.owner_occupied == 'Yes' else 'No',
            'Property_Class': lead.property_class,
            'Ownership': lead.ownership,
            'Listing_Agreement_Type': lead.listing_agreement_type,
            'Agent_Name': f"{lead.list_agent_first_name or ''} {lead.list_agent_last_name or ''}",
            'Office_Name': lead.list_office_name,
            'Remarks': lead.remarks_private,
            'Notes': lead.notes,
        })
    
    # Fetch data from the CRM table
    crm_data = db.query(CRM).all()
    crm_entries = []
    for entry in crm_data:
        crm_entries.append({
            'customer_id': entry.id,
            'customer_name': entry.name,
            'customer_email': entry.email,
            'customer_notes': entry.notes,
        })
    
    db.close()  
    
    templates = request.app.state.templates
    return templates.TemplateResponse("leads.html", {"request": request, "leads": leads, "crm_entries": crm_entries})

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
    data = {
        'FromEmail': SENDER,
        'FromName': email, 
        'Subject': 'New Contact Form Submission',
        'Text-part': 'Hey Toni, here is another support lead!',
        'Html-part': f'''
            <p>First Name: {first_name}</p>
            <p>Last Name: {last_name}</p>
            <p>Email: {email}</p>
            <p>Phone: {phone}</p>
            <p>General Inquiry: {general_inquiry}</p>
        ''',        
        'Recipients': [{ "Email": RECIPIENT }]
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://api.mailjet.com/v3/send',
                json=data,
                auth=(MAILJET_API, MAILJET_SECRET)
            )        
        logger.info(f"Mailjet response status code: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"Mailjet error: {response.text}")
            raise HTTPException(status_code=500, detail="Error sending email")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Error sending email")
    logger.info("Contact form submission successful, redirecting user.")
    return RedirectResponse(url="/contact", status_code=303)


@router.get("/resources", response_class=HTMLResponse, name="resources")
async def resources(request: Request):
    logger.info("Rendering resources page")
    templates = request.app.state.templates
    return templates.TemplateResponse("resources.html", {"request": request})


#########################################
############ ANLYTICS ROTUES ############
#########################################
@router.get("/api/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
 #   try:
 #       ip_address = request.client.host
 #       hostname = request.headers.get('Host', '')
 #       credentials = service_account.Credentials.from_service_account_file('services/yonehomes-50e3014c6fd5.json')
 #       client = BetaAnalyticsDataClient(credentials=credentials)
 #       property_id = '461503351'
 #       end_date = datetime.now().date()
 #       start_date = end_date - timedelta(days=30)
 #       ga_request = RunReportRequest(
 #           property=f"properties/{property_id}",
 #           date_ranges=[DateRange(start_date=start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"))],
 #           metrics=[
 #               Metric(name="activeUsers"),
 #               Metric(name="averageSessionDuration"),
 #               Metric(name="bounceRate"),
 #               Metric(name="newUsers"),
 #               Metric(name="screenPageViewsPerSession"),
 #               Metric(name="scrolledUsers"),
 #               Metric(name="sessions"),
 #               Metric(name="userEngagementDuration"),
 #           ],
 #           dimensions=[
 #               Dimension(name="city"),
 #               Dimension(name="country"),
 #               Dimension(name="date"),
 #               Dimension(name="language"),
 #               Dimension(name="pageTitle"),
 #               Dimension(name="landingPage"),
 #           ]
 #       )
 #       response = client.run_report(ga_request)
 #       # Database processing
 #       db = analytics_sessionLocal()
 #       analytics = db.query(Analytics).filter(
 #           (Analytics.ip_address == ip_address) & (Analytics.hostname == hostname)
 #       ).first()
 #       if not analytics:
 #           analytics = Analytics(ip_address=ip_address, hostname=hostname)
 #           db.add(analytics)
 #           db.flush()
 #       else:
 #           analytics.last_seen = datetime.now()
 #       for row in response.rows:
 #           date = datetime.strptime(row.dimension_values[2].value, "%Y%m%d").date()
 #           sub_table_entry = SubTable(
 #               analytics_id=analytics.id,
 #               ip_address=ip_address,
 #               hostname=hostname,
 #               date=date,
 #               sessions=int(float(row.metric_values[6].value)),
 #               new_users=int(float(row.metric_values[3].value)),
 #               active_users=int(float(row.metric_values[0].value)),
 #               average_session_duration=float(row.metric_values[1].value),
 #               bounce_rate=float(row.metric_values[2].value),
 #               screen_page_views_per_session=float(row.metric_values[4].value),
 #               scrolled_users=int(float(row.metric_values[5].value)),
 #               user_engagement_time=int(float(row.metric_values[7].value)),
 #               city=row.dimension_values[0].value,
 #               country=row.dimension_values[1].value,
 #               language=row.dimension_values[3].value,
 #               page_title=row.dimension_values[4].value,
 #               landing_page=row.dimension_values[5].value,
 #           )
 #           db.add(sub_table_entry)
 #       db.commit()
 #       dashboard_data = get_dashboard_data(db)
        templates = request.app.state.templates
        return templates.TemplateResponse("dashboard.html", {"request": request})
 #   except Exception as e:
 #       logger.error(f"Unexpected error in dashboard route: {str(e)}")
 #       raise HTTPException(status_code=500, detail="An unexpected error occurred")


#@router.get('/api/dashboard_database')
#async def dashboard_analytics(request: Request):
#    try:
#        main = get_analytics_from_db()
#        sub = get_sub_table_from_db()
#        return {
#            "analytics": main,
#            "subtable": sub
#        }
#    except Exception as e:
#        raise HTTPException(status_code=500, detail=str(e))

#def get_dashboard_data(db, days: int = 30) -> Dict[str, Any]:
#    end_date = datetime.now().date()
#    start_date = end_date - timedelta(days=days)
#    
#    analytics_data = db.query(SubTable).filter(
#        SubTable.date >= start_date,
#        SubTable.date <= end_date
#    ).all()
#    return {
#        "total_sessions": calculate_total_sessions(analytics_data), # Total Sessions
#        "total_users": calculate_total_users(analytics_data), # Total Users
#        "new_users": calculate_new_users(analytics_data), # New Users
#        "active_users": calculate_active_users(analytics_data), # Active Users
#        "user_engagement_duration": calculate_total_user_engagement_duration(analytics_data), # User Engagement Duration
#        "avg_session_duration": calculate_avg_session_duration(analytics_data), # Average Session Duration
#        "bounce_rate": calculate_bounce_rate(analytics_data), # Bounce Rate
#        "screen_page_views_per_session": calculate_avg_screens_per_session(analytics_data), # Screen Page Views Per Session
#        "scrolled_users": calculate_total_scrolled_users(analytics_data), # Scrolled Users
#        "city": calculate_city(analytics_data), # City
#        "country": calculate_country(analytics_data), # Country
#        "language": calculate_language(analytics_data), # Language
#        "page_title": calculate_page_title(analytics_data), # Page Title
#        "landing_page": calculate_landing_page(analytics_data), # Landing Page
#    }

#def get_analytics_data(db_session, days: int = 30) -> List[Analytics]:
#    """Retrieve analytics data for the specified number of days."""
#    end_date = datetime.now().date()
#    start_date = end_date - timedelta(days=days)  # This uses timedelta correctly
#    return db_session.query(Analytics).filter(
#        Analytics.date >= start_date,
#        Analytics.date <= end_date
#    ).order_by(desc(Analytics.date)).all()
#
#
#def calculate_total_sessions(analytics_data: List[Analytics]) -> int:
#    """Calculate total sessions for the given period."""
#    return sum(data.sessions for data in analytics_data)
#
#def calculate_total_users(analytics_data: List[Analytics]) -> int:
#    """Calculate total unique users for the given period."""
#    return sum(data.new_users for data in analytics_data)
#
#def calculate_new_users(analytics_data: List[Analytics]) -> int:
#    """Calculate total new users for the given period."""
#    return sum(data.new_users for data in analytics_data)
#
#def calculate_active_users(analytics_data: List[Analytics]) -> int:
#    """Calculate total active users for the given period."""
#    return sum(data.active_users for data in analytics_data)
#
#def calculate_total_user_engagement_duration(analytics_data: List[Analytics]) -> int:
#    """Calculate total user engagement duration for the given period."""
#    return sum(data.user_engagement_time for data in analytics_data)
#
#def calculate_avg_session_duration(analytics_data: List[Analytics]) -> float:
#    """Calculate average session duration for the given period."""
#    total_duration = sum(data.average_session_duration for data in analytics_data)
#    total_sessions = calculate_total_sessions(analytics_data)
#    return total_duration / total_sessions if total_sessions > 0 else 0
#
#def calculate_bounce_rate(analytics_data: List[Analytics]) -> float:
#    """Calculate bounce rate for the given period."""
#    total_sessions = calculate_total_sessions(analytics_data)
#    bounced_sessions = sum(1 for data in analytics_data if data.bounce_rate < 100)  # Adjust as needed
#    return (bounced_sessions / total_sessions) * 100 if total_sessions > 0 else 0
#
#def calculate_avg_screens_per_session(analytics_data: List[Analytics]) -> float:
#    """Calculate average screen page views per session."""
#    total_screens = sum(data.screen_page_views_per_session for data in analytics_data)
#    total_sessions = calculate_total_sessions(analytics_data)
#    return total_screens / total_sessions if total_sessions > 0 else 0
#
#def calculate_total_scrolled_users(analytics_data: List[Analytics]) -> int:
#    """Calculate total scrolled users for the given period."""
#    return sum(data.scrolled_users for data in analytics_data)
#
#def calculate_language(analytics_data: List[Analytics]) -> str:
#    """Get the most common language."""
#    languages = [data.language for data in analytics_data]
#    return Counter(languages).most_common(1)[0][0] if languages else ""
#
#
#def calculate_city(analytics_data: List[Analytics]) -> str:
#    """Get the most common city."""
#    cities = [data.city for data in analytics_data]
#    return Counter(cities).most_common(1)[0][0] if cities else ""
#
#def calculate_country(analytics_data: List[Analytics]) -> str:
#    """Get the most common country."""
#    countries = [data.country for data in analytics_data]
#    return Counter(countries).most_common(1)[0][0] if countries else ""
#
#
#def calculate_page_title(analytics_data: List[Analytics]) -> str:
#    """Calculate the most common page title."""
#    page_titles = [data.page_title for data in analytics_data]
#    return Counter(page_titles).most_common(1)[0][0] if page_titles else ""
#
#def calculate_landing_page(analytics_data: List[Analytics]) -> str:
#    """Calculate the most common landing page."""
#    landing_pages = [data.landing_page for data in analytics_data]
#    return Counter(landing_pages).most_common(1)[0][0] if landing_pages else ""
#
#def calculate_user_age_brackets(analytics_data: List[Analytics]) -> Counter:
#    """Calculate the count of users for each age bracket."""
#    age_brackets = [data.user_age_bracket for data in analytics_data if data.user_age_bracket]
#    return Counter(age_brackets)
#
#def calculate_user_genders(analytics_data: List[Analytics]) -> Counter:
#    """Calculate the count of users for each gender."""
#    genders = [data.user_gender for data in analytics_data if data.user_gender]
#    return Counter(genders)
#

#########################################
############ POPULATE TABLES ############
#########################################
@router.get("/api/populate_homes_database", response_model=dict, name="import")
async def get_home_data(background_tasks: BackgroundTasks, request: Request, concurrency_limit: int = 10,  max_retries: int = 20, delay: int= 1, timeout: int = 300, min_images: int = 2, max_images: int = 100, max_price: int = 500000):
    logger.info("Starting MLS homes gathering task")
    background_tasks.add_task(start_homes, concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay)
    return JSONResponse(content={"message": "MLS data gathering home task started in the background"})

@router.get("/api/populate_rentals_database", response_model=dict, name="import")
async def get_rental_data(background_tasks: BackgroundTasks, request: Request, concurrency_limit: int = 10,  max_retries: int = 20, delay: int= 1, timeout: int = 300, min_images: int = 2, max_images: int = 50, max_price: int =3000):
    logger.info("Starting MLS rentals gathering task")
    background_tasks.add_task(start_rentals, concurrency_limit, timeout, max_images, min_images, max_price, max_retries, delay)
    return JSONResponse(content={"message": "MLS data gathering rental task started in the background"})

@router.get("/api/populate_leads_database", response_model=dict, name="import_leads")
async def get_leads_data(background_tasks: BackgroundTasks, request: Request, concurrency_limit: int = 10,  max_retries: int = 20, delay: int=1):
    logger.info("Starting MLS leads gathering task")
    background_tasks.add_task(start_leads, concurrency_limit, max_retries, delay)
    return JSONResponse(content={"message": "MLS data gathering leads task started in the background"})


######################################
############ VIEW TABLES ############
######################################
@router.get('/view_homes_database')
async def api_homes(request: Request):
    try:
        listings_data = get_homes_from_db()
        return {"homes":listings_data}
    except Exception:
        raise HTTPException(status_code=500)

@router.get('/view_rentals_database')
async def api_rentals(request: Request):
    try:
        listings_data = get_rentals_from_db()
        return {"rentals":listings_data}
    except Exception:
        raise HTTPException(status_code=500)


######################################
############ TABLE COUNTS ############
######################################
@router.get('/count_homes_database')
async def get_total_count(request: Request):
    try:
        listings_data = get_homes_from_db()
        return {"homes count":len(listings_data)}
    except Exception:
        raise HTTPException(status_code=500)
    
@router.get('/count_rentals_database')
async def get_total_count(request: Request):
    try:
        listings_data = get_rentals_from_db()
        return {"rentals Count":len(listings_data)}
    except Exception:
        raise HTTPException(status_code=500)




#####################################
############ NOTES ROUTE ############
#####################################
@router.post("/get_notes", response_model=NoteResponse)  # Changed to POST and specify the response model
async def get_notes(request: Request): 
    data = await request.json()  
    logger.info(f"Received data: {data}")
    
    if not isinstance(data, dict) or 'mls' not in data:
        raise HTTPException(status_code=400, detail='Invalid data format or missing MLS')
    
    notes_data = get_notes_from_db(data)
    logger.info(notes_data)
    
    if notes_data:
        clean_notes = [note.notes.replace('\n', ' ').strip() for note in notes_data]
        return {"notes": clean_notes}
    
    return {"notes": []}
    

@router.post("/save_notes")
async def save_notes(request: Request):
    data = await request.json()
    logger.info(f"Received data: {data}")  
    if not isinstance(data, dict) or 'mls' not in data:
        raise HTTPException(status_code=400, detail='Invalid data format or missing MLS')
    
    saved_data = save_notes_from_db(data)
    return saved_data


@router.post("/delete_notes")  # Keep this as POST
async def delete_notes(request: Request):
    data = await request.json()
    logger.info(f"Received data: {data}") 

    if not isinstance(data, dict) or 'mls' not in data:
        raise HTTPException(status_code=400, detail='Invalid data format or missing MLS')

    response = delete_notes_from_db(data)

    if response: 
        return {"message": "Notes deleted successfully", "data": response}
    else:
        raise HTTPException(status_code=404, detail='Notes not found or could not be deleted')


###################################
############ CRM ROUTE ############
###################################
@router.post("/save_customer_info")
async def save_customer_info(request: Request):
    data = await request.json()
    logger.info(f"Received data: {data}")  

    if not isinstance(data, dict) or not all(key in data for key in ['name', 'email', 'notes']):
        raise HTTPException(status_code=400, detail='Invalid data format or missing fields')

    customer_data = {
        'name': data['name'],
        'email': data['email'],
        'notes': data['notes']
    }
    saved_data = save_customer_info_in_db(customer_data)
    return saved_data



@router.post("/delete_customer_info") 
async def delete_customer_info(request: Request):
    data = await request.json()
    logger.info(f"Received data: {data}") 

    if not isinstance(data, dict) or 'id' not in data:
        raise HTTPException(status_code=400, detail='Invalid data format or missing ID')

    response = delete_notes_from_db(data)

    if response: 
        return response  # Return the message directly
    else:
        raise HTTPException(status_code=404, detail='Notes not found or could not be deleted')



####################
####### LEADS ######
####################
class ContactCreate(BaseModel):
    name: str
    email: str
    notes: str = ''

class ContactResponse(ContactCreate):
    id: int

@router.post("/create_contacts/", response_model=ContactResponse)
def create_contact(contact: ContactCreate):
    db = leads_sessionLocal()
    try:
        db_contact = CRM(**contact.model_dump())
        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)
        return db_contact
    finally:
        db.close()

@router.get("/create_contacts/", response_model=List[ContactResponse])
def read_contacts(skip: int = 0):
    db = leads_sessionLocal()
    try:
        contacts = db.query(CRM).offset(skip).all() 
        return contacts
    finally:
        db.close()


@router.delete("/delete_contact/{contact_id}/", response_model=dict)
def delete_contact(contact_id: int):
    db = leads_sessionLocal()
    try:
        contact = db.query(CRM).filter(CRM.id == contact_id).first()
        if contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        db.delete(contact)
        db.commit()
        return {"message": f"Contact {contact_id} deleted successfully"}
    finally:
        db.close()


from fastapi import HTTPException

# Define a new ContactUpdate model for updating notes
class ContactUpdate(BaseModel):
    notes: str

@router.put("/update_contact/{contact_id}/", response_model=ContactResponse)
def update_contact(contact_id: int, contact: ContactUpdate):
    db = leads_sessionLocal()
    try:
        db_contact = db.query(CRM).filter(CRM.id == contact_id).first()
        if db_contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        db_contact.notes = contact.notes
        db.commit()
        db.refresh(db_contact)
        return db_contact
    finally:
        db.close()


@router.get("/leads2", response_class=HTMLResponse, name="leads2")
async def leads2(request: Request):
    logger.info("Rendering leads2 page")
    templates = request.app.state.templates
    return templates.TemplateResponse("leads2.html", {"request": request})

