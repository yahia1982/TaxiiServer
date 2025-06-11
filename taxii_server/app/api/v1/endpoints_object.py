from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body, status
from sqlalchemy.orm import Session
import uuid
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from app.crud import crud_taxii
from app.schemas import taxii_schemas
from app.core.database import get_db
# from bfore_auth import types as bfore_types # Removed as we use local principal dict
from app.auth.dependencies import get_current_principal, ROLE_LITE_FEED
from app.api.v1.endpoints_api_root import get_api_root_or_404
from app.api.v1.endpoints_collection import get_collection_or_404
from app.api.v1.permissions import check_read_permission, check_write_permission
from app.crud.crud_taxii import _parse_stix_modified
router = APIRouter()
@router.get("/{api_root_path}/collections/{collection_id}/objects/", response_model=taxii_schemas.ObjectsEnvelope, summary="Get Objects from Collection", tags=["Objects"])
async def get_objects_from_collection(api_root_path: str, collection_id: str, request: Request, db: Session = Depends(get_db), current_principal: Dict[str, Any] = Depends(get_current_principal), added_after: Optional[datetime] = Query(None), match_id: Optional[str] = Query(None, alias="match[id]"), match_type: Optional[str] = Query(None, alias="match[type]"), match_version: Optional[str] = Query(None, alias="match[version]"), limit: Optional[int] = Query(None, ge=1), next_val: Optional[str] = Query(None, alias="next")):
    db_api_root = get_api_root_or_404(db, api_root_path)
    db_collection = get_collection_or_404(db, db_api_root.id, collection_id)
    check_read_permission(db_collection, current_principal)
    stix_ids = match_id.split(',') if match_id else None
    stix_types = match_type.split(',') if match_type else None
    stix_versions_dt = None
    if match_version and match_version not in ["all", "last"]:
        try: stix_versions_dt = [_parse_stix_modified(v.strip()) for v in match_version.split(',')]
        except ValueError as e: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid STIX version format: {e}")
    if match_version == "last" and (not stix_ids or len(stix_ids) != 1): raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="match[version]=last requires a single STIX ID in match[id].")
    offset = int(next_val) if next_val and next_val.isdigit() else 0
    db_objects_orm = []
    if match_version == "last" and stix_ids and len(stix_ids) == 1:
        latest_versions = crud_taxii.stored_object["get_all_versions_by_id"](db, collection_id=db_collection.id, stix_id=stix_ids[0], user_scopes=[current_principal["role"]] if current_principal.get("role") == ROLE_LITE_FEED else None)
        if latest_versions: db_objects_orm = [latest_versions[0]]
    else:
        db_objects_orm = crud_taxii.stored_object["get_multi_from_collection"](db, collection_id=db_collection.id, user_scopes=[current_principal["role"]] if current_principal.get("role") == ROLE_LITE_FEED else None, added_after=added_after, stix_ids=stix_ids, stix_types=stix_types, stix_versions_dt=stix_versions_dt, limit=limit, offset=offset)
    objects_data = [obj.object for obj in db_objects_orm]
    next_page_url = None
    if limit and len(db_objects_orm) == limit: next_page_url = str(request.url.replace_query_params(next=str(offset + limit)))
    return taxii_schemas.ObjectsEnvelope(objects=objects_data, more=bool(next_page_url), next=next_page_url)
@router.post("/{api_root_path}/collections/{collection_id}/objects/", response_model=taxii_schemas.Status, status_code=status.HTTP_202_ACCEPTED, summary="Add Object(s) to Collection", tags=["Objects"])
async def add_objects_to_collection(api_root_path: str, collection_id: str, bundle: taxii_schemas.STIXBundle = Body(...), db: Session = Depends(get_db), current_principal: Dict[str, Any] = Depends(get_current_principal)):
    db_api_root = get_api_root_or_404(db, api_root_path)
    db_collection = get_collection_or_404(db, db_api_root.id, collection_id)
    check_write_permission(db_collection, current_principal)
    success_ids, failure_details = [], []
    req_timestamp = datetime.now(timezone.utc)
    for stix_obj_data in bundle.objects:
        obj_id_for_report = stix_obj_data.get("id", "unknown")
        try:
            if not isinstance(stix_obj_data, dict) or not all(k in stix_obj_data for k in ["id", "type", "modified"]): raise ValueError("Object is not a valid STIX object or missing required fields.")
            crud_taxii.stored_object["add"](db=db, collection_id=db_collection.id, stix_object_data=stix_obj_data)
            success_ids.append(stix_obj_data["id"])
        except ValueError as e: failure_details.append({"id": obj_id_for_report, "message": str(e)})
        except Exception as e: failure_details.append({"id": obj_id_for_report, "message": f"Internal server error processing object: {str(e)}"})
    current_status = "complete" if not failure_details else "partial" if success_ids else "failure"
    return taxii_schemas.Status(id=str(uuid.uuid4()), status=current_status, request_timestamp=req_timestamp, total_count=len(bundle.objects), success_count=len(success_ids), failure_count=len(failure_details), pending_count=0, successes=success_ids or None, failures=[{"id": f["id"], "message": f["message"]} for f in failure_details] if failure_details else None)
@router.get("/{api_root_path}/collections/{collection_id}/objects/{object_id}/", response_model=taxii_schemas.ObjectsEnvelope, summary="Get Object by STIX ID", tags=["Objects"])
async def get_object_by_stix_id(api_root_path: str, collection_id: str, object_id: str, db: Session = Depends(get_db), current_principal: Dict[str, Any] = Depends(get_current_principal), match_version: Optional[str] = Query(None, alias="match[version]")):
    db_api_root = get_api_root_or_404(db, api_root_path)
    db_collection = get_collection_or_404(db, db_api_root.id, collection_id)
    check_read_permission(db_collection, current_principal)
    db_objects_orm = []
    if match_version == "last":
        all_versions = crud_taxii.stored_object["get_all_versions_by_id"](db, collection_id=db_collection.id, stix_id=object_id, user_scopes=[current_principal["role"]] if current_principal.get("role") == ROLE_LITE_FEED else None)
        if all_versions: db_objects_orm = [all_versions[0]]
    elif match_version and match_version != "all":
        try: versions_dt = [_parse_stix_modified(v.strip()) for v in match_version.split(',')]
        except ValueError as e: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid STIX version format: {e}")
        all_versions = crud_taxii.stored_object["get_all_versions_by_id"](db, collection_id=db_collection.id, stix_id=object_id, user_scopes=[current_principal["role"]] if current_principal.get("role") == ROLE_LITE_FEED else None)
        db_objects_orm = [obj for obj in all_versions if obj.stix_modified_timestamp in versions_dt]
    else: # "all" or no version specified
        db_objects_orm = crud_taxii.stored_object["get_all_versions_by_id"](db, collection_id=db_collection.id, stix_id=object_id, user_scopes=[current_principal["role"]] if current_principal.get("role") == ROLE_LITE_FEED else None)
    if not db_objects_orm: raise HTTPException(status_code=404, detail=f"Object '{object_id}' with specified versions not found.")
    return taxii_schemas.ObjectsEnvelope(objects=[obj.object for obj in db_objects_orm])
