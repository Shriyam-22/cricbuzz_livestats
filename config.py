"""Central configuration for Cricbuzz LiveStats.

All settings are read from environment variables (loaded from the .env file),
so no secret is ever written in the code.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- Cricbuzz API (RapidAPI) -------------------------------------------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")
API_BASE_URL = f"https://{RAPIDAPI_HOST}"
API_TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT_SECONDS", "15"))
API_CACHE_MINUTES = int(os.getenv("API_CACHE_MINUTES", "5"))

# --- Database ----------------------------------------------------------------
# DB_ENGINE can be "sqlite" (default, no install needed), "mysql" or "postgresql".
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", BASE_DIR / "data" / "cricbuzz.db"))
if not SQLITE_PATH.is_absolute():
    SQLITE_PATH = BASE_DIR / SQLITE_PATH  # relative paths are relative to the project folder

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306" if DB_ENGINE == "mysql" else "5432"))
DB_NAME = os.getenv("DB_NAME", "cricbuzz")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"
