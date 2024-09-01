import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from start_files.config import get_templates
from start_files.routes.routes import router
from start_files.models.users.users import init_db

# Initialize the database

def create_app() -> FastAPI:
    app = FastAPI()

    # Mount static files directory
    app.mount("/static", StaticFiles(directory="start_files/static"), name="static")
    
    # Include routers
    app.include_router(router)
    
    #Initialize DB
    init_db()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("/var/www/html/fastapi_project/logs/app.log")
        ]
    )
    
    # Register templates
    templates = get_templates()
    app.state.templates = templates
    
    return app
