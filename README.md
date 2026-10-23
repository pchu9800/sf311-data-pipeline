# SF 311 Service Requests ETL Pipeline

A Python and PostgreSQL data engineering project that extracts San Francisco 311 service requests, validates and transforms records, and provides SQL reporting views for service request analysis.

## Business Objective

Build a repeatable pipeline to help analyze:

- Service request volume over time
- Complaint categories and neighborhood trends
- Average service request resolution times
- New and updated service requests

## Architecture

**SF 311 API → Bronze (Raw JSON) → Silver (Clean JSON) → PostgreSQL → Gold (SQL Views)**

The pipeline uses `updated_datetime` to identify changed records and a PostgreSQL checkpoint to track successful processing windows.

## Technology Stack

- **Python:** Requests, Pandas, Psycopg
- **Database:** PostgreSQL
- **SQL:** Upserts, aggregations, reporting views
- **Testing:** Pytest and unittest.mock
- **Version Control:** Git and GitHub

## Project Structure

| File | Purpose |
|---|---|
| `extract.py` | API requests, retries, pagination, raw data extraction |
| `transform.py` | Data validation, cleaning, and resolution-time calculations |
| `load.py` | PostgreSQL table creation, upserts, and Gold views |
| `pipeline.py` | ETL orchestration and checkpoint management |
| `sql/gold_views.sql` | Monthly, neighborhood, and service category reporting |
| `tests/` | Transformation and pipeline tests |
| `exploration.py` | Initial exploratory data analysis |

## Key Engineering Features

- Incremental extraction using update timestamps
- Paginated REST API requests with retry handling
- Raw and cleaned data layers
- Required-field and data-quality validation
- PostgreSQL upserts using unique request IDs
- Transaction-based checkpoint updates
- SQL reporting views
- Automated unit tests and basic logging

## Local Setup

Requires Python 3.13 and a running PostgreSQL server.

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies using `pip install -r requirements.txt`.
4. Create a PostgreSQL database named `sf311_pipeline`.
5. Run the unit tests with `python -m pytest -v`.
6. Run `python pipeline.py` to execute the incremental workflow. The script prompts for the PostgreSQL password.

**Note:** The incremental extraction workflow has a known API limitation described below. A complete unattended run is not yet guaranteed.

## Testing

- 7 transformation tests passed
- 3 pipeline orchestration tests passed
- PostgreSQL upsert behavior verified
- PostgreSQL transaction rollback independently verified

## Known Limitations

**HTTP 428:** The SF 311 API has returned HTTP 428 during larger paginated extractions, sometimes after successfully returning earlier pages. The exact cause remains unresolved.

The project currently uses offset-based pagination. This can be affected by source records changing during extraction.

Incremental extraction and checkpoint logic are implemented, but reliable unattended execution has not been established. Scheduling and advanced pagination improvements are intentionally deferred.

## Data Source

[San Francisco Open Data — 311 Cases](https://data.sfgov.org/City-Infrastructure/311-Cases/vw6y-z8j6)

## Project Scope

This is a portfolio ETL prototype focused on foundational Data Engineering practices, data quality, SQL, and pipeline design rather than production-scale infrastructure.
