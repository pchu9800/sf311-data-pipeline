
import pandas as pd
import pytest

from transform import (
    validate_raw_data,
    transform_data,
    validate_transformed_data
)


# --- TEST DATA ---

def sample_data():

    # Create one valid service request
    return pd.DataFrame([{
        "service_request_id": "101",
        "requested_datetime": "2026-10-01T10:00:00",
        "updated_datetime": "2026-10-01T15:00:00",
        "closed_date": "2026-10-01T15:00:00",
        "status_description": "Closed"
    }])


# --- TEST 1: VALID DATA ---

def test_valid_transformation():

    df = sample_data()

    validate_raw_data(df)
    result = transform_data(df)
    validate_transformed_data(result)

    # Resolution time should be 5 hours
    assert result["resolution_hours"].iloc[0] == 5.0


# --- TEST 2: INVALID ID TYPE ---

def test_invalid_id_type():

    df = sample_data()

    # Allow mixed data types for testing
    df["service_request_id"] = df["service_request_id"].astype(object)

    # Replace string ID with integer
    df.loc[0, "service_request_id"] = 101

    # Our validation should reject non-string IDs
    with pytest.raises(ValueError):
        validate_raw_data(df)


# --- TEST 3: DUPLICATE IDs ---

def test_duplicate_ids():

    df = sample_data()

    # Add another record with the same ID
    df = pd.concat([df, df], ignore_index=True)

    # Validate after transformation
    validate_raw_data(df)
    result = transform_data(df)

    with pytest.raises(ValueError):
        validate_transformed_data(result)


# --- TEST 4: EMPTY ID ---

def test_empty_id():

    df = sample_data()

    # Whitespace becomes empty after stripping
    df.loc[0, "service_request_id"] = "   "

    result = transform_data(df)

    with pytest.raises(ValueError):
        validate_transformed_data(result)


# --- TEST 5: INVALID DATE ---

def test_invalid_date():

    df = sample_data()

    # Replace required date with invalid text
    df.loc[0, "requested_datetime"] = "invalid_date"

    result = transform_data(df)

    with pytest.raises(ValueError):
        validate_transformed_data(result)


# --- TEST 6: NEGATIVE RESOLUTION TIME ---

def test_negative_resolution():

    df = sample_data()

    # Closing date is earlier than request date
    df.loc[0, "closed_date"] = "2026-09-30T10:00:00"

    result = transform_data(df)

    with pytest.raises(ValueError):
        validate_transformed_data(result)


# --- TEST 7: MISSING OPTIONAL CLOSING DATE ---

def test_missing_closed_date():

    df = sample_data()

    # Simulate an open request without closed_date
    df["status_description"] = "Open"
    df = df.drop(columns=["closed_date"])

    result = transform_data(df)

    # Missing closing date should remain valid
    validate_transformed_data(result)

    assert pd.isna(result["resolution_hours"].iloc[0])


# --- TEST 8: OPEN REQUEST WITH CLOSING DATE ---

def test_open_request_resolution():

    df = sample_data()

    # Request has a closing date but status is Open
    df["status_description"] = "Open"

    result = transform_data(df)
    validate_transformed_data(result)

    # Resolution hours must remain null
    assert pd.isna(result["resolution_hours"].iloc[0])