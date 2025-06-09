from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from app.crud import crud_taxii
from app.schemas import taxii_schemas
from app.core.database import get_db
from bfore_auth import types as bfore_types
from app.auth.dependencies import get_current_active_user
from app.api.v1.endpoints_api_root import get_api_root_or_404
from app.api.v1.endpoints_collection import get_collection_or_404
from app.api.v1.permissions import check_read_permission
from app.crud.crud_taxii import _parse_stix_modified
router = APIRouter()
@router.get("/{api_root_path}/collections/{collection_id}/manifest/", response_model=taxii_schemas.Manifest, summary="Get Collection Manifest", tags=["Manifests"])
async def get_collection_manifest(api_root_path: str, collection_id: str, request: Request, db: Session = Depends(get_db), current_user: bfore_types.User = Depends(get_current_user), added_after: Optional[datetime] = Query(None), match_id: Optional[str] = Query(None, alias="match[id]"), match_type: Optional[str] = Query(None, alias="match[type]"), match_version: Optional[str] = Query(None, alias="match[version]"), limit: Optional[int] = Query(None, ge=1), next_val: Optional[str] = Query(None, alias="next")):
    db_api_root = get_api_root_or_404(db, api_root_path)
    db_collection = get_collection_or_404(db, db_api_root.id, collection_id)
    check_read_permission(db_collection, current_user)
    stix_ids = match_id.split(',') if match_id else None
    stix_types = match_type.split(',') if match_type else None
    stix_versions_dt = None
    if match_version and match_version not in ["all", "last"]:
        try: stix_versions_dt = [_parse_stix_modified(v.strip()) for v in match_version.split(',')]
        except ValueError as e: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid STIX version format: {e}")
    if match_version == "last": raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="match[version]=last for manifests is not yet implemented.")
    offset = int(next_val) if next_val and next_val.isdigit() else 0
    db_records = crud_taxii.manifest_record["get_multi_from_collection"](db, collection_id=db_collection.id, added_after=added_after, stix_ids=stix_ids, stix_types=stix_types, stix_versions_dt=stix_versions_dt, limit=limit, offset=offset, user_scopes=current_user.scopes)
    manifest_records_resp = []
    for rec in db_records:
        date_added = rec.date_added_to_collection.replace(tzinfo=timezone.utc) if rec.date_added_to_collection.tzinfo is None else rec.date_added_to_collection
        version_ts = rec.stix_modified_timestamp.replace(tzinfo=timezone.utc) if rec.stix_modified_timestamp.tzinfo is None else rec.stix_modified_timestamp
        manifest_records_resp.append(taxii_schemas.ManifestRecord(id=rec.stix_id, date_added=date_added, version=version_ts.isoformat().replace("+00:00", "Z"), media_type=rec.media_type))
    next_page_url = None
    if limit and len(db_records) == limit: next_page_url = str(request.url.replace_query_params(next=str(offset + limit)))
    return taxii_schemas.Manifest(objects=manifest_records_resp, more=bool(next_page_url), next=next_page_url)
