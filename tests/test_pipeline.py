
from unittest.mock import MagicMock, patch

import pytest

from pipeline import run_pipeline


# --- TEST SETUP ---

def mock_database():

    # Create a fake database connection
    connection = MagicMock()

    # Create a fake database cursor
    cursor = (
        connection.__enter__.return_value
        .cursor.return_value.__enter__.return_value
    )

    # Simulate no previous checkpoint
    cursor.fetchone.return_value = None

    return connection, cursor


def checkpoint_written(cursor):

    # Check whether the checkpoint update was executed
    return any(
        "INSERT INTO pipeline_state" in call.args[0]
        for call in cursor.execute.call_args_list
    )


# --- TEST 1: EMPTY EXTRACTION ---

def test_empty_extraction():

    connection, cursor = mock_database()

    # Simulate an API response containing zero records
    with (
        patch("pipeline.psycopg.connect", return_value=connection),
        patch("pipeline.getpass", return_value="test"),
        patch("pipeline.extract_requests", return_value=[]),
        patch("pipeline.save_raw_data"),
    ):
        run_pipeline()

    # An empty successful run should advance the checkpoint
    assert checkpoint_written(cursor)


# --- TEST 2: FAILED EXTRACTION ---

def test_failed_extraction():

    connection, cursor = mock_database()

    # Simulate an API failure
    with (
        patch("pipeline.psycopg.connect", return_value=connection),
        patch("pipeline.getpass", return_value="test"),
        patch(
            "pipeline.extract_requests",
            side_effect=RuntimeError("Simulated API failure")
        ),
    ):

        # The pipeline should propagate the error
        with pytest.raises(RuntimeError):
            run_pipeline()

    # A failed extraction must not update the checkpoint
    assert not checkpoint_written(cursor)




# --- TEST 3: SUCCESSFUL LOAD ---

def test_successful_load():

    connection, cursor = mock_database()

    # Simulate one extracted record
    records = [{"service_request_id": "101"}]

    # Create a fake DataFrame
    df = MagicMock()

    # Replace external operations with mocks
    with (
        patch("pipeline.psycopg.connect", return_value=connection),
        patch("pipeline.getpass", return_value="test"),
        patch("pipeline.extract_requests", return_value=records),
        patch("pipeline.save_raw_data"),
        patch("pipeline.read_raw_data", return_value=df),
        patch("pipeline.validate_raw_data"),
        patch("pipeline.transform_data", return_value=df),
        patch("pipeline.validate_transformed_data"),
        patch("pipeline.save_silver_data"),
        patch("pipeline.read_silver_data", return_value=records),
        patch("pipeline.create_table"),
        patch("pipeline.load_records") as mock_load,
        patch("pipeline.create_gold_views") as mock_gold,
    ):
        run_pipeline()

    # Verify that records were passed to the loader
    mock_load.assert_called_once_with(cursor, records)

    # Verify Gold views were created
    mock_gold.assert_called_once_with(cursor)

    # Verify checkpoint update was executed
    assert checkpoint_written(cursor)
