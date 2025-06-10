import os
import sys
from datetime import datetime, timezone
import uuid
import argparse
from typing import Optional, List, Dict, Any  # Added List, Dict, Any

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
MYSQL_USER = os.getenv("MYSQL_USER", "yahia")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Algerie@213")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "JarvisStaging")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

TARGET_API_ROOT_TITLE = "Default API Root"
TARGET_COLLECTION_TITLE = "Domain Intelligence Patterns (MySQL)"
TARGET_COLLECTION_DESCRIPTION = (
    "Domain names, related indicators, and relationships ingested from MySQL."
)
TARGET_COLLECTION_ALIAS = "prod_domain_patterns_mysql"

# Namespaces for generating STIX IDs (can be any valid UUID)
DOMAIN_NAME_NAMESPACE = uuid.UUID("00abed46-aa71-4483-9513-298389290705")
INDICATOR_NAMESPACE = uuid.UUID(
    "00abed46-bb72-5594-0624-309490301816"
)  # Different namespace for indicators


def generate_domain_indicator_pattern_bundle(
    domain_id: int,
    domain_name: str,
    score: float,
    processed_time: datetime,
    updated_time: Optional[datetime],
) -> List[Dict[str, Any]]:
    """Generates a list containing domain-name, indicator, and relationship STIX objects."""
    bundle = []
    current_time_utc = datetime.now(timezone.utc)
    current_time_iso = current_time_utc.isoformat().replace("+00:00", "Z")
    current_time_iso_precise = (
        current_time_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    )

    # 1. Create domain-name SDO
    domain_name_id = f"domain-name--{uuid.uuid5(DOMAIN_NAME_NAMESPACE, domain_name)}"
    domain_name_sdo = {
        "type": "domain-name",
        "spec_version": "2.1",
        "id": domain_name_id,
        "value": domain_name,
        # created, modified, and x_custom_* fields are omitted as per user feedback
    }
    bundle.append(domain_name_sdo)

    # 2. Create indicator SDO
    indicator_pattern = f"[domain-name:value = '{domain_name}']"
    indicator_id = f"indicator--{uuid.uuid5(INDICATOR_NAMESPACE, domain_name)}"
    indicator_sdo = {
        "type": "indicator",
        "spec_version": "2.1",
        "id": indicator_id,
        "pattern": indicator_pattern,
        "pattern_type": "stix",
        "name": "Malicious Domain",
        "labels": ["malicious-activity"],
        "confidence": int(score * 100),
        "created": current_time_iso,
        "modified": current_time_iso,
        "valid_from": current_time_iso_precise,  # STIX spec requires specific precision for valid_from
    }
    bundle.append(indicator_sdo)

    # 3. Create relationship SRO (indicator based-on domain-name)
    relationship_id = f"relationship--{uuid.uuid4()}"
    relationship_sro = {
        "type": "relationship",
        "spec_version": "2.1",
        "id": relationship_id,
        "relationship_type": "based-on",
        "source_ref": indicator_id,  # Indicator is the source
        "target_ref": domain_name_id,  # Domain-name is the target
        "created": current_time_iso,
        "modified": current_time_iso,
    }
    bundle.append(relationship_sro)

    return bundle


def get_or_create_target_collection(
    db: Session,
    api_root_title: str,
    collection_title: str,
    collection_alias: str,
    collection_desc: str,
) -> CollectionModel:
    # This function remains largely the same as before
    api_roots = crud_taxii.api_root["get_multi"](db, limit=100)
    target_api_root = next(
        (root for root in api_roots if root.title == api_root_title), None
    )
    if not target_api_root:
        print(f"API Root '{api_root_title}' not found. Creating it.")
        target_api_root = crud_taxii.api_root["create"](
            db,
            title=api_root_title,
            description="API Root for ingested data.",
            max_content_length=10 * 1024 * 1024,
        )
        print(f"Created API Root: {target_api_root.title} (ID: {target_api_root.id})")
    target_collection = None
    if collection_alias:
        target_collection = crud_taxii.collection["get_by_alias"](
            db, alias=collection_alias, api_root_id=target_api_root.id
        )
    if not target_collection:
        collections_in_root = crud_taxii.collection["get_for_api_root"](
            db, api_root_id=target_api_root.id
        )
        target_collection = next(
            (coll for coll in collections_in_root if coll.title == collection_title),
            None,
        )
    if not target_collection:
        print(f"Collection '{collection_title}' not found. Creating it.")
        target_collection = crud_taxii.collection["create"](
            db,
            api_root_id=target_api_root.id,
            title=collection_title,
            description=collection_desc,
            alias=collection_alias,
            is_public_readable=False,
        )
        print(
            f"Created Collection: {target_collection.title} (ID: {target_collection.id})"
        )
    else:
        print(
            f"Found target Collection: {target_collection.title} (ID: {target_collection.id})"
        )
    return target_collection


def main(limit_rows: Optional[int] = None):
    print("Starting data ingestion from MySQL for STIX Patterns...")
    taxii_db: Session = TaxiiSessionLocal()
    mysql_conn = None
    cursor = None
    try:
        target_collection = get_or_create_target_collection(
            taxii_db,
            TARGET_API_ROOT_TITLE,
            TARGET_COLLECTION_TITLE,
            TARGET_COLLECTION_ALIAS,
            TARGET_COLLECTION_DESCRIPTION,
        )
        if not target_collection:
            return
        mysql_conn = mysql.connector.connect(
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            host=MYSQL_HOST,
            database=MYSQL_DATABASE,
            port=MYSQL_PORT,
        )
        cursor = mysql_conn.cursor(dictionary=True)
        query = "SELECT domainId, domainName, score, processed, updated FROM domainStateless"
        if limit_rows is not None:
            query += f" LIMIT {limit_rows}"
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Fetched {len(rows)} domains to process into patterns.")
        total_stix_objects_ingested = 0
        error_count = 0
        for i, row in enumerate(rows):
            try:
                stix_bundle = generate_domain_indicator_pattern_bundle(
                    domain_id=row["domainId"],
                    domain_name=row["domainName"],
                    score=row["score"],
                    processed_time=row["processed"],
                    updated_time=row["updated"],
                )
                for stix_object in stix_bundle:
                    crud_taxii.stored_object["add"](
                        db=taxii_db,
                        collection_id=target_collection.id,
                        stix_object_data=stix_object,
                    )
                    total_stix_objects_ingested += 1
                if (i + 1) % 50 == 0:
                    print(
                        f"Processed {i + 1} domains, ingested {total_stix_objects_ingested} STIX objects..."
                    )
            except ValueError as ve:
                print(
                    f"  Error converting data for domain {row.get('domainName', 'N/A')}: {ve}"
                )
                error_count += 1
            except Exception as e:
                print(
                    f"  Error ingesting pattern for domain {row.get('domainName', 'N/A')}: {e}"
                )
                error_count += 1
        print(
            f"Pattern ingestion complete. Total STIX objects ingested: {total_stix_objects_ingested}. Domains with errors: {error_count}."
        )
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if mysql_conn and mysql_conn.is_connected():
            mysql_conn.close()
            print("MySQL connection closed.")
        if taxii_db:
            taxii_db.close()
            print("TAXII DB session closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest domain data from MySQL as STIX indicator patterns into TAXII server."
    )
    parser.add_argument(
        "--limit", type=int, help="Limit the number of domains to process from MySQL."
    )
    args = parser.parse_args()
    main(limit_rows=args.limit)
