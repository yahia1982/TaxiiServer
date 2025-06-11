from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import uuid
from app.crud import crud_taxii
from app.schemas import taxii_schemas
from app.core.database import get_db
from app.models.taxii_models import ApiRoot as ApiRootModel
from typing import Dict, Any # Added
from app.auth.dependencies import get_current_principal, ROLE_ADMIN # Updated

router = APIRouter()

def get_api_root_or_404(db: Session, api_root_path_str: str) -> ApiRootModel:
    try: api_root_uuid = uuid.UUID(api_root_path_str)
    except ValueError: raise HTTPException(status_code=404, detail=f"Invalid API Root path format (expected UUID): {api_root_path_str}")
    api_root = crud_taxii.api_root["get"](db, api_root_id=api_root_uuid)
    if not api_root: raise HTTPException(status_code=404, detail=f"API Root '{api_root_path_str}' not found")
    return api_root

@router.get("/{api_root_path}/", response_model=taxii_schemas.ApiRoot, summary="Get API Root Information", tags=["API Root"])
async def get_api_root_info(api_root_path: str, db: Session = Depends(get_db)):
    db_api_root = get_api_root_or_404(db, api_root_path)
    return taxii_schemas.ApiRoot(
        title=db_api_root.title, description=db_api_root.description,
        versions=db_api_root.versions, max_content_length=db_api_root.max_content_length
    )

@router.get("/{api_root_path}/collections/", response_model=taxii_schemas.Collections, summary="List Collections in an API Root", tags=["Collections"])
async def list_collections_in_api_root(api_root_path: str, db: Session = Depends(get_db), current_principal: Dict[str, Any] = Depends(get_current_principal)):
    db_api_root = get_api_root_or_404(db, api_root_path)
    db_collections = crud_taxii.collection["get_for_api_root"](db, api_root_id=db_api_root.id)
    collections_resp = []
    principal_role = current_principal.get("role")

    for coll in db_collections:
        # Determine read access based on principal's role
        # This logic might need to be more aligned with check_read_permission if it becomes complex
        is_admin = principal_role == ROLE_ADMIN
        can_read_based_on_role = is_admin or \
                                 (principal_role in ["consumer", "publisher", "full_access_user", "lite_feed_user"]) # Using constants or defined roles

        can_read = coll.is_public_readable or can_read_based_on_role

        if can_read:
            can_write_based_on_role = is_admin or \
                                      (principal_role in ["publisher", "full_access_user"])
            can_write = can_write_based_on_role

            collections_resp.append(taxii_schemas.Collection(
                id=coll.id, title=coll.title, description=coll.description, alias=coll.alias,
                can_read=True,  # If it's in this list, user can read it
                can_write=can_write,
                media_types=coll.media_types
            ))
    return taxii_schemas.Collections(collections=collections_resp)
