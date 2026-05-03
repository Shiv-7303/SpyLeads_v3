"""app/utils/helpers.py — Common utility functions."""
import re
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def get_ist_now() -> datetime:
    return datetime.now(pytz.utc).astimezone(IST)

def extract_email_from_bio(bio: str) -> str:
    if not bio:
        return ""
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", bio)
    return match.group(0) if match else ""
