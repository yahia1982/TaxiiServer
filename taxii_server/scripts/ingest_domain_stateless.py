import os
import sys
from datetime import datetime, timezone
import uuid
import argparse
from typing import Optional

# Add project root to Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.append(PROJECT_ROOT)

import mysql.connector
from sqlalchemy.orm import Session

from app.core.database import SessionLocal as TaxiiSessionLocal
from app.crud import crud_taxii
from app.models.taxii_models import Collection as CollectionModel

# --- Configuration ---
MYSQL_USER = os.getenv("MYSQL_USER", "your_mysql_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "your_mysql_password")
MYSQL_HOST = os.getenv("MYSQL_HOST", "your_mysql_host")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "your_mysql_database_name")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

TARGET_API_ROOT_TITLE = "Default API Root"
TARGET_COLLECTION_TITLE = "Domain Intelligence from Production MySQL"
TARGET_COLLECTION_DESCRIPTION = "Domain names and scores ingested from the production domainStateless MySQL table."
TARGET_COLLECTION_ALIAS = "prod_domain_intel_mysql"

def create_stix_domain_name_object(domain_id: int, domain_name: str, score: float, processed_time: datetime, updated_time: Optional[datetime]) -> dict:
    namespace_uuid = uuid.UUID("00abed46-aa71-4483-9513-298389290705")
    stix_id = f"domain-name--{uuid.uuid5(namespace_uuid, domain_name)}"
    created_time = processed_time.astimezone(timezone.utc) if processed_time.tzinfo is None else processed_time
    modified_time = updated_time or processed_time
    modified_time = modified_time.astimezone(timezone.utc) if modified_time.tzinfo is None else modified_time
    stix_object = {
        "type": "domain-name",
        "spec_version": "2.1",
        "id": stix_id,
        "value": domain_name,
        "created": created_time.isoformat().replace("+00:00", "Z"),
        "modified": modified_time.isoformat().replace("+00:00", "Z"),
        "x_custom_score": score,
        "x_custom_source_domain_id": domain_id,
        "x_custom_processed_time": processed_time.isoformat()
    }
    if updated_time:
        stix_object["x_custom_updated_time"] = updated_time.isoformat()
    return stix_object

def get_or_create_target_collection(db: Session, api_root_title: str, collection_title: str, collection_alias: str, collection_desc: str) -> CollectionModel:
    api_roots = crud_taxii.api_root["get_multi"](db, limit=100)
    target_api_root = next((root for root in api_roots if root.title == api_root_title), None)
    if not target_api_root:
        print(f"API Root '{api_root_title}' not found. Creating it.")
        target_api_root = crud_taxii.api_root["create"](db, title=api_root_title, description="API Root for ingested data.", max_content_length=10 * 1024 * 1024)
        print(f"Created API Root: {target_api_root.title} (ID: {target_api_root.id})")
    target_collection = None
    if collection_alias:
        target_collection = crud_taxii.collection["get_by_alias"](db, alias=collection_alias, api_root_id=target_api_root.id)
    if not target_collection:
        collections_in_root = crud_taxii.collection["get_for_api_root"](db, api_root_id=target_api_root.id)
        target_collection = next((coll for coll in collections_in_root if coll.title == collection_title), None)
    if not target_collection:
        print(f"Collection '{collection_title}' not found. Creating it.")
        target_collection = crud_taxii.collection["create"](db, api_root_id=target_api_root.id, title=collection_title, description=collection_desc, alias=collection_alias, is_public_readable=False)
        print(f"Created Collection: {target_collection.title} (ID: {target_collection.id})")
    else:
        print(f"Found target Collection: {target_collection.title} (ID: {target_collection.id})")
    return target_collection

def main(limit_rows: Optional[int] = None):
    print("Starting data ingestion from MySQL domainStateless table...")
    print(f"MySQL Config: User={MYSQL_USER}, Host={MYSQL_HOST}, DB={MYSQL_DATABASE}, Port={MYSQL_PORT}")
    taxii_db: Session = TaxiiSessionLocal()
    mysql_conn = None
    cursor = None
    try:
        target_collection = get_or_create_target_collection(taxii_db, TARGET_API_ROOT_TITLE, TARGET_COLLECTION_TITLE, TARGET_COLLECTION_ALIAS, TARGET_COLLECTION_DESCRIPTION)
        if not target_collection:
            print("Error: Could not find or create target TAXII collection. Aborting.")
            return
        print(f"Connecting to MySQL database '{MYSQL_DATABASE}' on host '{MYSQL_HOST}'...")
        mysql_conn = mysql.connector.connect(user=MYSQL_USER, password=MYSQL_PASSWORD, host=MYSQL_HOST, database=MYSQL_DATABASE, port=MYSQL_PORT)
        cursor = mysql_conn.cursor(dictionary=True)
        query = "SELECT domainId, domainName, score, processed, updated FROM domainStateless"
        if limit_rows is not None:
            query += f" LIMIT {limit_rows}"
        print(f"Executing query: {query}")
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Fetched {len(rows)} rows from domainStateless.")
        ingested_count = 0
        error_count = 0
        for row in rows:
            try:
                domain_name = row['domainName']
                stix_do = create_stix_domain_name_object(domain_id=row['domainId'], domain_name=domain_name, score=row['score'], processed_time=row['processed'], updated_time=row['updated'])
                crud_taxii.stored_object["add"](db=taxii_db, collection_id=target_collection.id, stix_object_data=stix_do)
                ingested_count += 1
                if ingested_count % 100 == 0 and ingested_count > 0:
                    print(f"Ingested {ingested_count} objects so far...")
            except ValueError as ve:
                print(f"  Error converting data for domain {row.get('domainName', 'N/A')}: {ve}")
                error_count += 1
            except Exception as e:
                print(f"  Error ingesting domain {row.get('domainName', 'N/A')}: {e}")
                error_count += 1
        print(f"Ingestion complete. Successfully ingested: {ingested_count} objects. Errors: {error_count}.")
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}. Check connection details and MySQL server.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if cursor: cursor.close()
        if mysql_conn and mysql_conn.is_connected(): mysql_conn.close(); print("MySQL connection closed.")
        if taxii_db: taxii_db.close(); print("TAXII DB session closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest domain data from MySQL into TAXII server.")
    parser.add_argument("--limit", type=int, help="Limit the number of rows to process from MySQL.")
    args = parser.parse_args()
    print("MySQL Ingestion Script")
    print("---------------------")
    print("Ensure that PYTHONPATH includes the project root for app imports.")
    print("Make sure database connection details (MySQL and TAXII's PostgreSQL) are correctly set as environment variables or in the script.")
    print("Run Alembic migrations for TAXII server ('alembic upgrade head') if the TAXII DB is new or schema changed.")
    main(limit_rows=args.limit)
