# start_files/app.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from start_files.config import get_templates
from start_files.routes.routes import router

def create_app() -> FastAPI:
    app = FastAPI()

    app.mount("/static", StaticFiles(directory="start_files/static"), name="static")

    templates = get_templates()
    app.state.templates = templates

    # Include routes from the router
    app.include_router(router)

    return app
