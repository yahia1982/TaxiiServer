from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime, timezone

from app.models.taxii_models import ApiRoot, Collection, StoredObject, ManifestRecord
# from app.schemas.taxii_schemas import STIXObject as STIXObjectSchema # Not directly used for creation here

# --- API Root CRUD ---
def get_api_root(db: Session, api_root_id: uuid.UUID) -> Optional[ApiRoot]:
    return db.query(ApiRoot).filter(ApiRoot.id == api_root_id).first()

def get_api_roots(db: Session, skip: int = 0, limit: int = 10) -> List[ApiRoot]:
    return db.query(ApiRoot).offset(skip).limit(limit).all()

def create_api_root(db: Session, title: str, description: Optional[str], max_content_length: int, versions: List[str] = None) -> ApiRoot:
    if versions is None:
        versions = ["taxii-2.1"]
    db_api_root = ApiRoot(
        title=title,
        description=description,
        versions=versions,
        max_content_length=max_content_length
    )
    db.add(db_api_root)
    db.commit()
    db.refresh(db_api_root)
    return db_api_root

# --- Collection CRUD ---
def get_collection(db: Session, collection_id: uuid.UUID, api_root_id: Optional[uuid.UUID] = None) -> Optional[Collection]:
    query = db.query(Collection).filter(Collection.id == collection_id)
    if api_root_id:
        query = query.filter(Collection.api_root_id == api_root_id)
    return query.first()

def get_collection_by_alias(db: Session, alias: str, api_root_id: Optional[uuid.UUID] = None) -> Optional[Collection]:
    query = db.query(Collection).filter(Collection.alias == alias)
    if api_root_id:
        query = query.filter(Collection.api_root_id == api_root_id)
    return query.first()

def get_collections_for_api_root(db: Session, api_root_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Collection]:
    return db.query(Collection).filter(Collection.api_root_id == api_root_id).offset(skip).limit(limit).all()

def create_collection(db: Session, api_root_id: uuid.UUID, title: str, description: Optional[str] = None, alias: Optional[str] = None, media_types: List[str] = None, is_public_readable: bool = False) -> Collection:
    if media_types is None:
        media_types = ["application/stix+json;version=2.1"]
    db_collection = Collection(
        api_root_id=api_root_id,
        title=title,
        description=description,
        alias=alias,
        media_types=media_types,
        is_public_readable=is_public_readable
    )
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection

# --- STIX Object (StoredObject) CRUD ---
def get_stix_object_by_stix_id_and_modified(db: Session, collection_id: uuid.UUID, stix_id: str, stix_modified: datetime) -> Optional[StoredObject]:
    return db.query(StoredObject).filter(
        StoredObject.collection_id == collection_id,
        StoredObject.stix_id == stix_id,
        StoredObject.stix_modified_timestamp == stix_modified
    ).first()

def get_stix_objects_by_stix_id(db: Session, collection_id: uuid.UUID, stix_id: str) -> List[StoredObject]:
    return db.query(StoredObject).filter(
        StoredObject.collection_id == collection_id,
        StoredObject.stix_id == stix_id
    ).order_by(StoredObject.stix_modified_timestamp.desc()).all()


def get_stix_objects_from_collection(
    db: Session,
    collection_id: uuid.UUID,
    added_after: Optional[datetime] = None,
    stix_ids: Optional[List[str]] = None,
    stix_types: Optional[List[str]] = None,
    stix_versions_dt: Optional[List[datetime]] = None, # list of 'modified' datetime objects
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[StoredObject]:
    query = db.query(StoredObject).filter(StoredObject.collection_id == collection_id)

    if added_after:
        # This uses the StoredObject's own db_created_at, not manifest's date_added.
        # For true TAXII 'added_after', manifest join is needed.
        sub_query = db.query(ManifestRecord.stix_id, ManifestRecord.stix_modified_timestamp).            filter(ManifestRecord.collection_id == collection_id, ManifestRecord.date_added_to_collection > added_after).subquery()

        query = query.join(sub_query, and_(
            StoredObject.stix_id == sub_query.c.stix_id,
            StoredObject.stix_modified_timestamp == sub_query.c.stix_modified_timestamp
        ))

    if stix_ids:
        query = query.filter(StoredObject.stix_id.in_(stix_ids))

    if stix_types:
        query = query.filter(StoredObject.type.in_(stix_types))

    if stix_versions_dt:
        query = query.filter(StoredObject.stix_modified_timestamp.in_(stix_versions_dt))

    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    return query.order_by(StoredObject.db_created_at.asc()).all()


def _parse_stix_modified(stix_modified_str: str) -> datetime:
    try:
        # Ensure it's offset-aware and in UTC if 'Z' is present
        if stix_modified_str.endswith('Z'):
            dt = datetime.fromisoformat(stix_modified_str[:-1] + '+00:00')
        else:
            dt = datetime.fromisoformat(stix_modified_str)
        # If timezone naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise ValueError(f"Invalid STIX modified timestamp format: {stix_modified_str}")


def add_stix_object(db: Session, collection_id: uuid.UUID, stix_object_data: Dict[str, Any]) -> StoredObject:
    stix_id = stix_object_data.get("id")
    stix_modified_str = stix_object_data.get("modified")
    stix_type = stix_object_data.get("type")
    spec_version = stix_object_data.get("spec_version", "2.1")

    if not all([stix_id, stix_modified_str, stix_type]):
        raise ValueError("STIX object data must include id, modified, and type fields.")

    parsed_modified_dt = _parse_stix_modified(stix_modified_str)

    db_obj = get_stix_object_by_stix_id_and_modified(db, collection_id, stix_id, parsed_modified_dt)

    if db_obj:
        db_obj.object = stix_object_data
        db_obj.db_modified_at = func.now()
    else:
        db_obj = StoredObject(
            collection_id=collection_id,
            stix_id=stix_id,
            type=stix_type,
            spec_version=spec_version,
            object=stix_object_data,
            stix_modified_timestamp=parsed_modified_dt
        )
        db.add(db_obj)

    db.commit()
    db.refresh(db_obj)

    manifest = db.query(ManifestRecord).filter(
        ManifestRecord.collection_id == collection_id,
        ManifestRecord.stix_id == stix_id,
        ManifestRecord.stix_modified_timestamp == parsed_modified_dt
    ).first()

    if not manifest:
        db_manifest_record = ManifestRecord(
            collection_id=collection_id,
            stix_id=stix_id,
            stix_modified_timestamp=parsed_modified_dt,
            media_type=f"application/stix+json;version={spec_version}"
        )
        db.add(db_manifest_record)
        db.commit()

    return db_obj

def delete_stix_object_version(db: Session, collection_id: uuid.UUID, stix_id: str, stix_modified: datetime) -> bool:
    obj_to_delete = get_stix_object_by_stix_id_and_modified(db, collection_id, stix_id, stix_modified)
    if not obj_to_delete:
        return False

    db.query(ManifestRecord).filter(
        ManifestRecord.collection_id == collection_id,
        ManifestRecord.stix_id == stix_id,
        ManifestRecord.stix_modified_timestamp == stix_modified
    ).delete(synchronize_session=False)

    db.delete(obj_to_delete)
    db.commit()
    return True

# --- Manifest Record CRUD ---
def get_manifest_records(
    db: Session,
    collection_id: uuid.UUID,
    added_after: Optional[datetime] = None,
    stix_ids: Optional[List[str]] = None,
    stix_types: Optional[List[str]] = None,
    stix_versions_dt: Optional[List[datetime]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    media_types: Optional[List[str]] = None
) -> List[ManifestRecord]:
    query = db.query(ManifestRecord).filter(ManifestRecord.collection_id == collection_id)

    if added_after:
        query = query.filter(ManifestRecord.date_added_to_collection > added_after)

    if stix_ids:
        query = query.filter(ManifestRecord.stix_id.in_(stix_ids))

    if stix_versions_dt:
        query = query.filter(ManifestRecord.stix_modified_timestamp.in_(stix_versions_dt))

    if media_types:
        query = query.filter(ManifestRecord.media_type.in_(media_types))

    if stix_types:
        # This join is crucial for filtering manifest by STIX object type
        query = query.join(StoredObject, and_(
            ManifestRecord.stix_id == StoredObject.stix_id,
            ManifestRecord.stix_modified_timestamp == StoredObject.stix_modified_timestamp, # Typo corrected
            ManifestRecord.collection_id == StoredObject.collection_id
        )).filter(StoredObject.type.in_(stix_types))

    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    return query.order_by(ManifestRecord.date_added_to_collection.asc()).all()


api_root = {
    "get": get_api_root,
    "get_multi": get_api_roots,
    "create": create_api_root,
}

collection = {
    "get": get_collection,
    "get_by_alias": get_collection_by_alias,
    "get_for_api_root": get_collections_for_api_root,
    "create": create_collection,
}

stored_object = {
    "get_by_id_and_modified": get_stix_object_by_stix_id_and_modified,
    "get_all_versions_by_id": get_stix_objects_by_stix_id,
    "get_multi_from_collection": get_stix_objects_from_collection,
    "add": add_stix_object,
    "delete_version": delete_stix_object_version,
}

manifest_record = {
    "get_multi_from_collection": get_manifest_records,
}
