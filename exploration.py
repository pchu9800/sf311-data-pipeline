
import requests
import pandas as pd

# --- 1. EXTRACT ---

# SF 311 API endpoint
url = "https://data.sfgov.org/resource/vw6y-z8j6.json"

# Get the 100 newest service requests
params = {
    "$limit": 100,
    "$order": "requested_datetime DESC"
}

# Request data from the API
try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
except requests.exceptions.RequestException as error:
    raise SystemExit(f"API request failed: {error}")

# Convert JSON into Python data
data = response.json()

# Check the expected response structure
if not isinstance(data, list) or not data:
    raise ValueError("API did not return a non-empty list of records")

# Convert records into a DataFrame
df = pd.DataFrame(data)

print(f"Extracted {len(df)} records")


# --- 2. INITIAL VALIDATION ---

# Check that important columns exist
required_columns = [
    "service_request_id",
    "requested_datetime",
    "updated_datetime",
    "status_description"
]

for column in required_columns:
    if column not in df.columns:
        raise ValueError(f"Missing required column: {column}")

# Add optional columns if the API omitted them
optional_columns = ["closed_date", "lat", "long"]

for column in optional_columns:
    if column not in df.columns:
        df[column] = None

# Count missing request IDs
missing_ids = df["service_request_id"].isna().sum()
print("Missing request IDs:", missing_ids)

# Count duplicate request IDs
duplicate_count = df["service_request_id"].duplicated().sum()
print("Duplicate request IDs:", duplicate_count)


# --- 3. TRANSFORM ---

# Convert date strings into datetime values
date_columns = [
    "requested_datetime",
    "updated_datetime",
    "closed_date"
]

for column in date_columns:
    df[column] = pd.to_datetime(df[column], errors="coerce")

# Convert coordinates into numbers
df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["long"] = pd.to_numeric(df["long"], errors="coerce")

# Calculate time from submission to closure
df["resolution_time"] = (
    df["closed_date"] - df["requested_datetime"]
)

# Convert resolution time into hours
df["resolution_hours"] = (
    df["resolution_time"] / pd.Timedelta(hours=1)
)


# --- 4. FINAL VALIDATION ---

# Count missing values in each column
print("\nMissing values:")
print(df.isna().sum())

# Compare status with missing closing dates
print("\nStatus vs missing closing date:")
print(pd.crosstab(
    df["status_description"],
    df["closed_date"].isna()
))

# Find closed requests
closed_df = df[df["status_description"] == "Closed"].copy()

# Find negative resolution times
invalid_resolution = closed_df[
    closed_df["resolution_hours"] < 0
]

print("Negative resolution times:", len(invalid_resolution))

# Find closed requests without a valid resolution time
missing_resolution = closed_df["resolution_hours"].isna().sum()
print("Closed requests missing resolution time:", missing_resolution)

# Find coordinates outside their valid ranges
invalid_coordinates = df[
    (df["lat"].notna() & ~df["lat"].between(-90, 90))
    | (df["long"].notna() & ~df["long"].between(-180, 180))
]

print("Invalid coordinates:", len(invalid_coordinates))


# --- 5. BUSINESS METRICS ---

# Keep closed requests with valid resolution times
valid_closed_df = closed_df[
    closed_df["resolution_hours"].notna()
    & (closed_df["resolution_hours"] >= 0)
]

# Calculate average resolution time
avg_resolution = valid_closed_df["resolution_hours"].mean()

print("\n--- BUSINESS METRICS ---")
print("Total requests:", len(df))
print("Closed requests:", len(closed_df))
print("Open requests:", (df["status_description"] == "Open").sum())

if pd.notna(avg_resolution):
    print(f"Average resolution time: {avg_resolution:.2f} hours")
else:
    print("Average resolution time: Not available")


# --- 6. VIEW RESULTS ---

# Show the first 5 closed requests
print("\nSample closed requests:")

print(closed_df[[
    "service_request_id",
    "requested_datetime",
    "closed_date",
    "resolution_hours"
]].head())
