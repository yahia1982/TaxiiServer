# TAXII 2.1 Server (FastAPI)

This project implements a TAXII 2.1 compliant server using FastAPI, SQLAlchemy, and PostgreSQL.

## Features

- TAXII 2.1 compliant (aims for core services: Discovery, API Root, Collections, Objects, Manifest)
- Built with Python, FastAPI (ASGI), SQLAlchemy (ORM), PostgreSQL (database)
- Authentication integrated with an external system via the `bfore_auth` library (stubs used in development).
- Role-based access control concepts: uses `is_admin` and `scopes` from the user object provided by `bfore_auth`.
- Special `lite-feed` scope: Users with this scope only receive data added to a collection more than 14 days ago.
- Data ingestion script provided to migrate data from a MySQL `domainStateless` table.

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
    cd taxii_server
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

    # JWT Settings (if bfore_auth doesn't fully manage token creation/validation, or for other app parts)
    # SECRET_KEY=a_very_secret_key_for_jwt_if_needed_locally
    # ALGORITHM=HS256
    # ACCESS_TOKEN_EXPIRE_MINUTES=30

    # For Data Ingestion Script (MySQL connection)
    MYSQL_USER=your_mysql_user
    MYSQL_PASSWORD=your_mysql_password
    MYSQL_HOST=your_mysql_host
    MYSQL_DATABASE=your_mysql_db_name
    MYSQL_PORT=3306

    # For initial superuser creation (if using the example init_db_command in main.py)
    # FIRST_SUPERUSER_USERNAME=admin
    # FIRST_SUPERUSER_PASSWORD=adminpassword
    # FIRST_SUPERUSER_EMAIL=admin@example.com
    ```
    **Note:** The application uses `pydantic-settings` to load these from the `.env` file.

5.  **Run Database Migrations:**
    Ensure your `alembic.ini` correctly points to your `DATABASE_URL` (it should pick up from the environment if configured).
    ```bash
    alembic upgrade head
    ```
    This will create all necessary tables in your PostgreSQL database.

6.  **(Optional) Initial Data Setup:**
    The application contains commented-out code in `app/main.py` (`init_db_command`) which can be enabled to create a default API Root and an initial admin user (if you are not managing these externally). You would typically run this once or adapt it into a separate CLI command.

## Running the Server

For development, run the Uvicorn server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The server will be available at `http://localhost:8000`.

## Running the Data Ingestion Script

The script ingests data from the MySQL `domainStateless` table into the TAXII server.

1.  Ensure MySQL environment variables (see Setup) are set.
2.  Run the script:
    ```bash
    python scripts/ingest_domain_stateless.py
    ```
    You can use the `--limit` argument to process a specific number of rows, e.g., `python scripts/ingest_domain_stateless.py --limit 100`.

## API Endpoints Overview

- **Interactive API Docs (Swagger UI):** Available at `/api/v1/docs` (assuming default `API_V1_STR` prefix).
- **Authentication:** Uses Bearer tokens. Tokens are expected to be obtained externally and validated by the `bfore_auth` system.
- **Key TAXII Endpoints (prefixed with `/api/v1/taxii2/`):**
    -   Discovery: `/` (e.g., `/api/v1/taxii2/`)
    -   API Root Info: `/{api_root_path}/`
    -   Collections: `/{api_root_path}/collections/`
    -   Collection Info: `/{api_root_path}/collections/{collection_id}/`
    -   Objects: `/{api_root_path}/collections/{collection_id}/objects/`
    -   Object by ID: `/{api_root_path}/collections/{collection_id}/objects/{object_id}/`
    -   Manifest: `/{api_root_path}/collections/{collection_id}/manifest/`
- **`lite-feed` Scope:** If a user's token grants the `lite-feed` scope (as determined by `bfore_auth`), their access to objects and manifests will be restricted to data that was added to the respective collection more than 14 days ago. Other users receive the most current data.

## Testing

Tests are written using PyTest.
1.  Ensure test dependencies are installed (should be covered by `requirements.txt`).
2.  Configure a test database if necessary (see `pytest.ini` for `SQLALCHEMY_DATABASE_URL` or use the default SQLite setup in `tests/conftest.py`).
3.  Run tests from the project root directory:
    ```bash
    pytest
    ```
