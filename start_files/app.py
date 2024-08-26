# start_files/app.py
import logging
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from start_files.config import get_templates
from start_files.routes.routes import router


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI()

    app.mount("/static", StaticFiles(directory="start_files/static"), name="static")

    templates = get_templates()
    app.state.templates = templates

    # Include routes from the router
    app.include_router(router)

    load_dotenv()
    

    return app
