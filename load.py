
import json
from pathlib import Path
from getpass import getpass

import psycopg


# --- CONFIGURATION ---

BASE_DIR = Path(__file__).resolve().parent

SILVER_FILE = BASE_DIR / "data" / "silver" / "sf311_clean.json"


# --- 1. READ SILVER DATA ---

def read_silver_data():

    # Load cleaned records
    with open(SILVER_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Expected a list of records")

    return records


# --- 2. CREATE TABLE ---

def create_table(cursor):

    # Create the database table if needed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_requests (
            service_request_id TEXT PRIMARY KEY,
            requested_datetime TIMESTAMP,
            updated_datetime TIMESTAMP,
            closed_date TIMESTAMP,
            status_description TEXT,
            service_name TEXT,
            analysis_neighborhood TEXT,
            lat DOUBLE PRECISION,
            long DOUBLE PRECISION,
            resolution_hours DOUBLE PRECISION
        )
    """)


# --- 3. CREATE GOLD VIEWS ---

def create_gold_views(cursor):

    # Find our SQL reporting file
    sql_file = BASE_DIR / "sql" / "gold_views.sql"

    # Read the SQL statements
    sql = sql_file.read_text(encoding="utf-8")

    # Create or update the Gold views
    cursor.execute(sql)

    print("Gold views created successfully")


# --- 4. LOAD DATA ---

def load_records(cursor, records):

    # SQL statement to insert or update records
    sql = """
        INSERT INTO service_requests (
            service_request_id,
            requested_datetime,
            updated_datetime,
            closed_date,
            status_description,
            service_name,
            analysis_neighborhood,
            lat,
            long,
            resolution_hours
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (service_request_id)
        DO UPDATE SET
            requested_datetime = EXCLUDED.requested_datetime,
            updated_datetime = EXCLUDED.updated_datetime,
            closed_date = EXCLUDED.closed_date,
            status_description = EXCLUDED.status_description,
            service_name = EXCLUDED.service_name,
            analysis_neighborhood = EXCLUDED.analysis_neighborhood,
            lat = EXCLUDED.lat,
            long = EXCLUDED.long,
            resolution_hours = EXCLUDED.resolution_hours
        WHERE service_requests.updated_datetime IS NULL
            OR EXCLUDED.updated_datetime >= service_requests.updated_datetime
    """

    # Select values for each database column
    values = [
        (
            record["service_request_id"],
            record.get("requested_datetime"),
            record.get("updated_datetime"),
            record.get("closed_date"),
            record.get("status_description"),
            record.get("service_name"),
            record.get("analysis_neighborhood"),
            record.get("lat"),
            record.get("long"),
            record.get("resolution_hours")
        )
        for record in records
    ]

    # Execute the inserts and updates
    cursor.executemany(sql, values)

    print(f"Loaded {len(values)} records into PostgreSQL")


# --- MAIN ---

if __name__ == "__main__":

    # Read validated Silver records
    records = read_silver_data()

    # Ask for database password without saving it in code
    password = getpass("PostgreSQL password: ")

    # Connect to our PostgreSQL database
    with psycopg.connect(
        host="localhost",
        port=5432,
        dbname="sf311_pipeline",
        user="postgres",
        password=password
    ) as connection:

        with connection.cursor() as cursor:

            # Create table and load records
            create_table(cursor)
            load_records(cursor, records)
            create_gold_views(cursor)

    # Connection commits changes if successful
    print("Database load completed successfully")
