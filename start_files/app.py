
# YONE_HISTORY_ROUTER_INTEGRATION
from start_files.history_archive import router as _yone_history_router

def _yone_attach_history(application):
    application.include_router(_yone_history_router)
    return application

from start_files.config import get_templates
from start_files.routes.routes import router
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
import logging

def create_app() -> FastAPI:
    app = _yone_attach_history(FastAPI())
    app.mount("/static", StaticFiles(directory="start_files/static"), name="static")
    app.include_router(router)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/test.yonehomes.log")
        ]
    )
    
    templates = get_templates()
    app.state.templates = templates
    
    return app
