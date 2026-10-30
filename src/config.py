import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Environment variable {name} not set")
    return value

ML_CLIENT_ID = _required("ML_CLIENT_ID")
ML_SECRET_KEY= _required("ML_SECRET_KEY")
ML_URL_REDIRECT = _required("ML_URL_REDIRECT")


TOKEN_PATH = BASE_DIR / "data" / "token.json"