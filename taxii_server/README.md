# TAXII 2.1 Server (FastAPI)

This project implements a TAXII 2.1 compliant server using FastAPI, SQLAlchemy, and PostgreSQL.
It supports both HTTP Basic Authentication (users stored locally) and API Key based authentication (with placeholder validation).

## Features

- TAXII 2.1 compliant services: Discovery, API Root, Collections, Objects, Manifest.
- Built with Python, FastAPI, SQLAlchemy, PostgreSQL.
- **Dual Authentication:**
    - HTTP Basic Authentication (username/password stored in the local database).
    - API Key Authentication (via `X-API-Key` header; validation logic is a placeholder for customization).
- **Role-Based Access Control (RBAC):** Users are assigned roles (e.g., `admin`, `full_access_user`, `lite_feed_user`) which determine permissions.
- **`lite-feed` Role:** Users with the `lite_feed_user` role only receive data added to a collection more than 14 days ago.
- **User Management Endpoints:** APIs for creating, listing, and managing users and their passwords.
- **Data Ingestion Script:** For migrating data from a MySQL `domainStateless` table, generating STIX patterns (`domain-name`, `indicator`, `relationship`).

## Prerequisites

- Python 3.8+
- PostgreSQL server
- MySQL server (for the data ingestion script)
- Pip, Alembic

## Setup Instructions

1.  **Clone & Setup Virtual Environment:** (Standard git clone, python -m venv venv, source venv/bin/activate)

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables (`.env` file):**
    ```env
    DATABASE_URL=postgresql://your_pg_user:your_pg_password@your_pg_host:5432/taxii_db
    # MySQL (for ingestion script)
    MYSQL_USER=your_mysql_user
    MYSQL_PASSWORD=your_mysql_password
    MYSQL_HOST=your_mysql_host
    MYSQL_DATABASE=your_mysql_db_name
    MYSQL_PORT=3306
    ```

4.  **Run Database Migrations:**
    ```bash
    alembic upgrade head
    ```

5.  **Initial User & Role Setup (Important!):**
    -   The application now uses local users and roles. You'll need to create them.
    -   **Admin User:** It's recommended to create an initial 'admin' role and an admin user.
        - You can do this via a Python script using the CRUD functions, or directly in the database if comfortable.
        - Example (conceptual script, adapt to run in your environment):
          ```python
          # from app.core.database import SessionLocal
          # from app.crud.crud_role import role_crud
          # from app.crud.crud_user import user_crud
          # from app.schemas.user_schemas import RoleCreate, UserCreate
          # db = SessionLocal()
          # admin_role = role_crud['get_by_name'](db, name='admin') or role_crud['create'](db, RoleCreate(name='admin', description='Administrator'))
          # user_crud['create'](db, UserCreate(username='admin', password='yoursecurepassword', role_name='admin'))
          # # Create other roles like 'lite_feed_user', 'full_access_user' as needed:
          # role_crud['create'](db, RoleCreate(name='lite_feed_user', description='Restricted feed access'))
          # role_crud['create'](db, RoleCreate(name='full_access_user', description='Full data access'))
          # db.close()
          ```
    -   The user management endpoints (see below) can be used once an admin user exists.

## Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Authentication

The server supports two authentication methods:
1.  **HTTP Basic Authentication:**
    -   Provide username and password via the HTTP Basic Auth header.
    -   Users and their hashed passwords are stored in the local database.
2.  **API Key Authentication:**
    -   Provide an API key in the `X-API-Key` request header.
    -   **Important:** The API key validation logic in `app/auth/apikey.py` is currently a placeholder. You **must** replace it with your actual validation mechanism to check keys against your external system.
    -   The placeholder includes test keys: `TEST_API_KEY_ADMIN`, `TEST_API_KEY_LITE`, `TEST_API_KEY_FULL` which assign corresponding roles.

## User Roles & Permissions

-   Users are assigned roles (e.g., `admin`, `full_access_user`, `lite_feed_user`).
-   **Admin (`admin` role):** Can access user management endpoints and typically has full access to all data.
-   **Lite Feed (`lite_feed_user` role):** Access to objects/manifests is restricted to data added to a collection more than 14 days ago.
-   Other roles can be defined and used for custom access control in the permission checking functions (`app/api/v1/permissions.py`).

## User Management Endpoints

Available under `/api/v1/users/`:
-   `POST /`: Create a new user (admin only).
-   `GET /`: List users (admin only).
-   `GET /{user_id}/`: Get user details (admin or self).
-   `PUT /{user_id}/`: Update user details (username, role, active status) (admin only).
-   `PUT /{user_id}/password/`: Update user's password (user themselves, or admin - admin part needs schema refinement).
-   `DELETE /{user_id}/`: Delete a user (admin only).

## MySQL Data Ingestion Script

(Content about MySQL ingestion script - generating STIX patterns - remains largely the same as per previous README update, ensure consistency)
The script `scripts/ingest_domain_stateless.py` ingests data from MySQL. For each domain, it generates a STIX pattern: `domain-name`, `indicator`, and `relationship`.
Details on generated object structures (static fields, 'now' timestamps, etc.) are in the script's comments or previous README versions.
Run with: `python scripts/ingest_domain_stateless.py [--limit N]`

## API Endpoints Overview (TAXII)

- Interactive API Docs (Swagger UI): `/api/v1/docs`.
- Key TAXII Endpoints (prefixed with `/api/v1/taxii2/`): (List of endpoints remains same)
    -   Discovery: `/`
    -   API Root Info: `/{api_root_path}/`
    -   ... (and so on)

## Testing

`pytest` from the project root.
