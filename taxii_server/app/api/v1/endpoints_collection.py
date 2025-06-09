from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from app.crud import crud_taxii
from app.schemas import taxii_schemas
from app.core.database import get_db
from app.models.taxii_models import Collection as CollectionModel
from app.models.user_models import User as UserModel
from app.auth.dependencies import get_current_active_user
from app.api.v1.endpoints_api_root import get_api_root_or_404
from app.api.v1.permissions import check_read_permission, check_write_permission

router = APIRouter()

def get_collection_or_404(db: Session, api_root_id: uuid.UUID, collection_id_str: str) -> CollectionModel:
    try: collection_uuid = uuid.UUID(collection_id_str)
    except ValueError: raise HTTPException(status_code=404, detail=f"Invalid Collection ID format: {collection_id_str}")
    collection = crud_taxii.collection["get"](db, collection_id=collection_uuid, api_root_id=api_root_id)
    if not collection: raise HTTPException(status_code=404, detail=f"Collection '{collection_id_str}' not found in API Root '{api_root_id}'")
    return collection

@router.get("/{api_root_path}/collections/{collection_id}/", response_model=taxii_schemas.Collection, summary="Get Collection Information", tags=["Collections"])
async def get_collection_info(api_root_path: str, collection_id: str, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_active_user)):
    db_api_root = get_api_root_or_404(db, api_root_path)
    db_collection = get_collection_or_404(db, db_api_root.id, collection_id)
    check_read_permission(db_collection, current_user)
    can_write = False
    try:
        check_write_permission(db_collection, current_user)
        can_write = True
    except HTTPException: pass
    return taxii_schemas.Collection(
        id=db_collection.id, title=db_collection.title, description=db_collection.description,
        alias=db_collection.alias, can_read=True, can_write=can_write, media_types=db_collection.media_types
    )
