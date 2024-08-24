from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse, name="home")
async def read_root(request: Request):
    from start_files.config import get_templates, flash, get_flashed_messages
    templates = get_templates()
    flash(request, "Welcome to Yone Homes!", "success")
    return templates.TemplateResponse("home.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/rentals", response_class=HTMLResponse, name="rentals")
async def rentals(request: Request):
    from start_files.config import get_templates, get_flashed_messages
    templates = get_templates()
    return templates.TemplateResponse("rentals.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/buying", response_class=HTMLResponse, name="buying")
async def buying(request: Request):
    from start_files.config import get_templates, get_flashed_messages
    templates = get_templates()
    return templates.TemplateResponse("buying.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/contact", response_class=HTMLResponse, name="contact")
async def contact(request: Request):
    from start_files.config import get_templates, get_flashed_messages
    templates = get_templates()
    return templates.TemplateResponse("contact.html", {"request": request, "flashed_messages": get_flashed_messages(request)})

@router.get("/resources", response_class=HTMLResponse, name="resources")
async def resources(request: Request):
    from start_files.config import get_templates, get_flashed_messages
    templates = get_templates()
    return templates.TemplateResponse("resources.html", {"request": request, "flashed_messages": get_flashed_messages(request)})
