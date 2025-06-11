from fastapi import HTTPException, status
from typing import Dict, Any # For principal dict

from app.models.taxii_models import Collection as CollectionModel
from app.auth.dependencies import ROLE_ADMIN, ROLE_LITE_FEED, ROLE_FULL_ACCESS # Assuming these are defined

def check_read_permission(collection: CollectionModel, principal: Dict[str, Any]):
    if collection.is_public_readable: return True
    if not principal: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required to read this collection.")
    user_role = principal.get("role")
    if user_role == ROLE_ADMIN: return True
    if user_role == ROLE_FULL_ACCESS: return True
    if user_role == ROLE_LITE_FEED: return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{user_role}' lacks read permission for this collection.")

def check_write_permission(collection: CollectionModel, principal: Dict[str, Any]):
    if not principal: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required to write to this collection.")
    user_role = principal.get("role")
    if user_role == ROLE_ADMIN: return True
    if user_role == "publisher" or user_role == ROLE_FULL_ACCESS : return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{user_role}' lacks write permission for this collection.")
