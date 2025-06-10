# TAXII 2.1 Server (FastAPI)

This project implements a TAXII 2.1 compliant server using FastAPI, SQLAlchemy, and PostgreSQL.

## Features

- TAXII 2.1 compliant (aims for core services: Discovery, API Root, Collections, Objects, Manifest)
- Built with Python, FastAPI (ASGI), SQLAlchemy (ORM), PostgreSQL (database)
- Authentication integrated with an external system via the `bfore_auth` library (stubs used in development).
- Role-based access control concepts: uses `is_admin` and `scopes` from the user object provided by `bfore_auth`.
- Special `lite-feed` scope: Users with this scope only receive data added to a collection more than 14 days ago.
- Data ingestion script provided to migrate data from a MySQL `domainStateless` table. This script generates a STIX pattern including a `domain-name`, an `indicator`, and a `relationship` object for each source domain.

## Prerequisites

- Python 3.8+
- PostgreSQL server (running and accessible)
- MySQL server (running and accessible, for the data ingestion script only)
- Access to the `bfore_auth` Python library/module (ensure it's installed in your environment).
- Pip (for installing Python packages)
- Alembic (installed via requirements, for database migrations)

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd taxii_server  # Assuming the project root is taxii_server
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root (`taxii_server/`) or set environment variables directly.
    Example `.env` content:
    ```env
    # PostgreSQL connection URL
    DATABASE_URL=postgresql://your_pg_user:your_pg_password@your_pg_host:5432/taxii_db

    # For Data Ingestion Script (MySQL connection)
    MYSQL_USER=your_mysql_user
    MYSQL_PASSWORD=your_mysql_password
    MYSQL_HOST=your_mysql_host
    MYSQL_DATABASE=your_mysql_db_name
    MYSQL_PORT=3306
    ```
    **Note:** The application uses `pydantic-settings` to load these from the `.env` file.

5.  **Run Database Migrations:**
    Ensure your `alembic.ini` correctly points to your `DATABASE_URL`.
    ```bash
    alembic upgrade head
    ```

## Running the Server

For development, run the Uvicorn server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running the MySQL Data Ingestion Script

The script ingests data from the MySQL `domainStateless` table into the TAXII server. For each domain, it generates a STIX pattern consisting of three objects: a `domain-name` SDO, an `indicator` SDO, and a `relationship` SRO linking them.

The generated STIX objects have the following characteristics:
-   **domain-name**: Contains only `id`, `type`, `spec_version`, and `value`. `created`, `modified`, and custom `x_custom_*` fields are omitted from this object.
-   **indicator**:
    -   Name: Static value "Malicious Domain".
    -   Labels: Static list `["malicious-activity"]`.
    -   Confidence: Derived from the source `score` field (multiplied by 100).
    -   Pattern: `[domain-name:value = 'THE_DOMAIN_NAME']`.
    -   Timestamps (`created`, `modified`, `valid_from`): Set to the time of script execution ("now").
-   **relationship**:
    -   Type: `based-on` (source: indicator, target: domain-name).
    -   Timestamps (`created`, `modified`): Set to the time of script execution ("now").

1.  Ensure MySQL environment variables (see Setup section) are set for user, password, host, database, and port.
2.  Run the script:
    ```bash
    python scripts/ingest_domain_stateless.py
    ```
    You can use the `--limit` argument to process a specific number of domains, e.g., `python scripts/ingest_domain_stateless.py --limit 100`.

## API Endpoints Overview

- **Interactive API Docs (Swagger UI):** Available at `/api/v1/docs`.
- **Authentication:** Uses Bearer tokens validated by the `bfore_auth` system.
- **Data Structure:** When querying objects, expect that data ingested by the MySQL script will include linked `domain-name`, `indicator`, and `relationship` objects.
- **Key TAXII Endpoints (prefixed with `/api/v1/taxii2/`):** (List of endpoints remains same)
    -   Discovery: `/`
    -   API Root Info: `/{api_root_path}/`
    -   Collections: `/{api_root_path}/collections/`
    -   Collection Info: `/{api_root_path}/collections/{collection_id}/`
    -   Objects: `/{api_root_path}/collections/{collection_id}/objects/`
    -   Object by ID: `/{api_root_path}/collections/{collection_id}/objects/{object_id}/`
    -   Manifest: `/{api_root_path}/collections/{collection_id}/manifest/`
- **`lite-feed` Scope:** Users with this scope will only see objects/manifest entries added to a collection more than 14 days ago.

## Testing

Tests are written using PyTest.
Run tests from the project root directory:
    ```bash
    pytest
    ```
