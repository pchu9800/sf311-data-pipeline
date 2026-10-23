
import psycopg
from getpass import getpass


# --- CONFIGURATION ---

TEST_ID = "__ROLLBACK_TEST__"

password = getpass("PostgreSQL password: ")

db_config = {
    "host": "localhost",
    "port": 5432,
    "dbname": "sf311_pipeline",
    "user": "postgres",
    "password": password
}


# --- 1. SIMULATE A FAILED TRANSACTION ---

class SimulatedFailure(Exception):
    pass


try:
    # Open a database transaction
    with psycopg.connect(**db_config) as connection:
        with connection.cursor() as cursor:

            # Ensure our test ID doesn't already exist
            cursor.execute(
                "SELECT 1 FROM service_requests WHERE service_request_id = %s",
                (TEST_ID,)
            )

            if cursor.fetchone():
                raise ValueError("Test ID already exists")

            # Insert a temporary test record
            cursor.execute(
                "INSERT INTO service_requests (service_request_id) VALUES (%s)",
                (TEST_ID,)
            )

            print("Test record inserted")

            # Simulate a pipeline failure before commit
            raise SimulatedFailure("Simulated pipeline failure")

except SimulatedFailure:
    print("Transaction rolled back")


# --- 2. VERIFY THE ROLLBACK ---

# Open a new database connection
with psycopg.connect(**db_config) as connection:
    with connection.cursor() as cursor:

        # Check whether the test record still exists
        cursor.execute(
            "SELECT COUNT(*) FROM service_requests WHERE service_request_id = %s",
            (TEST_ID,)
        )

        count = cursor.fetchone()[0]

# A successful rollback leaves no test record
assert count == 0, "Rollback failed"

print("PASS: No test record remains in PostgreSQL")
