import json
from pathlib import Path

import pandas as pd


# --- CONFIGURATION ---

BASE_DIR = Path(__file__).resolve().parent

BRONZE_FILE = BASE_DIR / "data" / "bronze" / "sf311_raw.json"
SILVER_FILE = BASE_DIR / "data" / "silver" / "sf311_clean.json"


# --- 1. READ RAW DATA ---

def read_raw_data():

    # Load original records from Bronze
    with open(BRONZE_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    # Check the expected data structure
    if not isinstance(records, list) or not records:
        raise ValueError("Expected a non-empty list of records")

    return pd.DataFrame(records)


# --- 2. INITIAL VALIDATION ---

def validate_raw_data(df):

    # Columns required for our pipeline
    required = [
        "service_request_id",
        "requested_datetime",
        "updated_datetime",
        "status_description"
    ]

    # Stop if a required column is missing
    for column in required:
        if column not in df.columns:
            raise ValueError(f"Missing required column: {column}")

    # Check for missing IDs
    if df["service_request_id"].isna().any():
        raise ValueError("Missing service request IDs")

    # Check for invalid primary key data types
    if not df["service_request_id"].map(lambda x: isinstance(x, str)).all():
        raise ValueError("Service request IDs must be strings")


# --- 3. TRANSFORM ---

def transform_data(df):

    # Work on a copy of the original DataFrame
    df = df.copy()

    # Standardize service request id
    df["service_request_id"] = (
        df["service_request_id"]
        .str.strip()
    )

    # Add and fill in optional columns if missing
    if "closed_date" not in df.columns:
        df["closed_date"] = None

    # Convert date columns
    date_columns = [
        "requested_datetime",
        "updated_datetime",
        "closed_date"
    ]

    for column in date_columns:
        df[column] = pd.to_datetime(df[column], errors="coerce")

    # Calculate resolution time
    df["resolution_time"] = (
        df["closed_date"] - df["requested_datetime"]
    )

    # Convert duration into hours
    df["resolution_hours"] = (
        df["resolution_time"] / pd.Timedelta(hours=1)
    )

    return df


# --- 4. FINAL VALIDATION ---

def validate_transformed_data(df):

    # Check for duplicate IDs
    if df["service_request_id"].duplicated().any():
        raise ValueError("Duplicate service request IDs")

    # Check for empty IDs
    if df["service_request_id"].eq("").any():
        raise ValueError("Empty service request IDs")

    # Required dates must be valid
    for column in ["requested_datetime", "updated_datetime"]:
        if df[column].isna().any():
            raise ValueError(f"Invalid or missing values in {column}")

    # Resolution time cannot be negative
    if (df["resolution_hours"] < 0).any():
        raise ValueError("Negative resolution times found")


# --- 5. SAVE CLEAN DATA ---

def save_silver_data(df):

    # Create Silver folder
    SILVER_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Save transformed records as JSON
    df.to_json(
        SILVER_FILE,
        orient="records",
        date_format="iso",
        indent=2
    )

    print(f"Saved {len(df)} clean records to Silver")


# --- MAIN ---

if __name__ == "__main__":

    df = read_raw_data()

    validate_raw_data(df)

    df = transform_data(df)

    validate_transformed_data(df)

    save_silver_data(df)