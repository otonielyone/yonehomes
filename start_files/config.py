# start_files/config.py

from typing import List, Dict, Union
from fastapi import Request
from fastapi.templating import Jinja2Templates

flash_messages = []

def flash(request: Request, message: str, category: str):
    """
    Store a flash message.
    """
    flash_messages.append({"message": message, "category": category})

def get_flashed_messages(request: Request) -> List[Dict[str, Union[str, List[str]]]]:
    """
    Retrieve all flash messages and clear them from the store.
    """
    messages = flash_messages[:]
    flash_messages.clear()
    return messages

def get_templates() -> Jinja2Templates:
    return Jinja2Templates(directory="start_files/templates")
