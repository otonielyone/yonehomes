# start_files/routes/routes.py

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter
from typing import Optional

router = APIRouter()

def route_url(request: Request, name: str, **params: Optional[dict]) -> str:
    """
    Generate a URL for a given route name.
    """
    return request.url_for(name, **params)

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

@router.get("/listings", response_class=RedirectResponse, name="listings")
async def listings(request: Request):
    return RedirectResponse(url="https://otonielyone.unitedrealestatewashingtondc.com/index.html")


@router.get("/contact", response_class=RedirectResponse, name="contact")
async def contact(request: Request):
    from start_files.config import get_templates, get_flashed_messages
    templates = get_templates()
    return templates.TemplateResponse("contact.html", {"request": request, "flashed_messages": get_flashed_messages(request)})


@router.get("/resources", response_class=RedirectResponse, name="resources")
async def resources(request: Request):
    from start_files.config import get_templates, get_flashed_messages
    templates = get_templates()
    return templates.TemplateResponse("resources.html", {"request": request, "flashed_messages": get_flashed_messages(request)})
