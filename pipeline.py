
from datetime import datetime, timedelta
from getpass import getpass
from zoneinfo import ZoneInfo

import logging
from pathlib import Path

import psycopg

from extract import extract_requests, save_raw_data

from transform import (
    read_raw_data,
    validate_raw_data,
    transform_data,
    validate_transformed_data,
    save_silver_data
)

from load import create_table, load_records, read_silver_data, create_gold_views

# --- LOGGING CONFIGURATION ---

# Create a folder for pipeline logs
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Save logs to a file and display them in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)


# --- CONFIGURATION ---

LOOKBACK_DAYS = 3


# --- RUN PIPELINE ---

def run_pipeline():

    # Use San Francisco local time for source timestamps
    end = datetime.now(
        ZoneInfo("America/Los_Angeles")
    ).replace(tzinfo=None) - timedelta(minutes=30)

    # Connect to PostgreSQL
    password = getpass("PostgreSQL password: ")

    with psycopg.connect(
        host="localhost",
        port=5432,
        dbname="sf311_pipeline",
        user="postgres",
        password=password
    ) as connection:

        with connection.cursor() as cursor:

            # Create a table to track successful runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_state (
                    pipeline_name TEXT PRIMARY KEY,
                    last_successful_end TIMESTAMP NOT NULL
                )
            """)

            # Read the previous successful checkpoint
            cursor.execute("""
                SELECT last_successful_end
                FROM pipeline_state
                WHERE pipeline_name = 'sf311'
                FOR UPDATE
            """)

            row = cursor.fetchone()
            checkpoint = row[0] if row else None

            # Avoid processing an already completed window
            if checkpoint is not None and end <= checkpoint:
                print("Already up to date")
                return

            # Recheck recent days for delayed updates
            start = (checkpoint or end) - timedelta(
                days=LOOKBACK_DAYS
            )

            print(f"Extracting updates from {start} to {end}")

            # Extract raw data
            records = extract_requests(start, end)
            save_raw_data(records)

            if records:

                # Read and validate Bronze data
                df = read_raw_data()
                validate_raw_data(df)

                # Transform and validate Silver data
                df = transform_data(df)
                validate_transformed_data(df)
                save_silver_data(df)

                # Load cleaned data into PostgreSQL
                create_table(cursor)
                load_records(cursor, read_silver_data())
                create_gold_views(cursor)

            else:
                print("No changed records in this window")

            # Save checkpoint in the same database transaction
            cursor.execute("""
                INSERT INTO pipeline_state (
                    pipeline_name,
                    last_successful_end
                )
                VALUES ('sf311', %s)
                ON CONFLICT (pipeline_name)
                DO UPDATE SET
                    last_successful_end = EXCLUDED.last_successful_end
            """, (end,))

    # The transaction has successfully committed
    print("Pipeline committed; checkpoint saved")


# --- MAIN ---

if __name__ == "__main__":

    try:
        # Record pipeline start
        logging.info("Pipeline started")

        run_pipeline()

        # Record successful completion
        logging.info("Pipeline completed successfully")

    except Exception:
        # Record error details and traceback
        logging.exception("Pipeline failed")
        raise
