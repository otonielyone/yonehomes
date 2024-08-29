# start_files/app.py
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from start_files.config import get_templates
from start_files.routes.routes import router



def create_app() -> FastAPI:
    app = FastAPI()

    app.mount("/static", StaticFiles(directory="start_files/static"), name="static")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("/var/www/html/fastapi_project/logs/app.log")
        ]
    )

    templates = get_templates()
    app.state.templates = templates
    
    router
    app.include_router(router)

    return app
