"""Quick check that the Cricbuzz API key works."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables

KEY = os.getenv("RAPIDAPI_KEY")
print("Key loaded:", KEY[:6] + "..." if KEY else None)  # debug: shows first 6 characters only

URL = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/recent"
HEADERS = {
    "X-RapidAPI-Key": KEY,
    "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com",
}

try:
    response = requests.get(URL, headers=HEADERS, timeout=10)
    print("Status:", response.status_code)
    print("Message:", response.text[:200])  # debug: what the API said
    response.raise_for_status()
    data = response.json()
    print("Top-level keys:", list(data.keys()))
except requests.exceptions.RequestException as err:
    print("Request failed:", err)