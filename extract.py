
import json
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime


# --- CONFIGURATION ---

API_URL = "https://data.sfgov.org/resource/vw6y-z8j6.json"
PAGE_SIZE = 500

BRONZE_DIR = Path(__file__).resolve().parent / "data" / "bronze"


# --- VALIDATE EXTRACTION WINDOW ---

def validate_window(start, end):

    # Ensure both values are datetimes
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise TypeError("Start and end must be datetime objects")

    # Ensure timestamps use our expected format
    if start.tzinfo is not None or end.tzinfo is not None:
        raise ValueError("Expected datetimes without timezone information")

    # Ensure the start comes before the end
    if start >= end:
        raise ValueError("Start must be earlier than end")


# --- EXTRACT ---


def extract_requests(start, end):

    # Validate the extraction window
    validate_window(start, end)

    # Filter records by their last update time
    window = (
        f"updated_datetime >= '{start.isoformat(timespec='seconds')}'"
        f" AND updated_datetime < '{end.isoformat(timespec='seconds')}'"
    )

    # Retry temporary server errors
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )

    # Create HTTP session with retries
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))

    records = []
    page = 0

    try:
        while True:

            # Request the next page of updated records
            params = {
                "$limit": PAGE_SIZE,
                "$offset": page * PAGE_SIZE,
                "$where": window,
                "$order": "updated_datetime ASC, service_request_id ASC"
            }

            # Send API request
            response = session.get(
                API_URL,
                params=params,
                timeout=30
            )

            # Display details if the API request fails
            if not response.ok:
                print("HTTP Status:", response.status_code)
                print("Response Headers:", dict(response.headers))
                print("API Error:", response.text[:2000])

            response.raise_for_status()

            # Parse JSON response
            batch = response.json()

            # Validate response structure
            if not isinstance(batch, list):
                raise ValueError("Unexpected API response format")

            # Stop when no more records are available
            if not batch:
                break

            # Collect the records
            records.extend(batch)

            print(f"Page {page + 1}: {len(batch)} records")

            # Stop if the final page is incomplete
            if len(batch) < PAGE_SIZE:
                break

            # Move to the next page
            page += 1

    finally:
        # Close HTTP session
        session.close()

    return records



# --- SAVE RAW DATA ---

def save_raw_data(records):

    # Create Bronze folder if missing
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)

    output_path = BRONZE_DIR / "sf311_raw.json"

    # Save JSON before transformations
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)

    print(f"Saved {len(records)} raw records")
