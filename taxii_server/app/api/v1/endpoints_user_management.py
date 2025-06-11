from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid

from app.core.database import get_db
from app.crud.crud_user import user_crud
from app.crud.crud_role import role_crud
from app.schemas.user_schemas import UserCreate, UserPublic, UserPasswordUpdate, AdminUserPasswordUpdate, UserUpdate
from app.auth.dependencies import get_current_principal, require_admin_principal, ROLE_ADMIN
from app.auth.security import verify_password # For current password check
from app.models.user_models import User as UserModel

router = APIRouter()

# --- Helper to get user or raise 404 ---
def get_user_or_404(db: Session, user_id: uuid.UUID) -> UserModel:
    user = user_crud["get"](db, user_id=user_id)
    if not user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    admin_principal: Dict[str, Any] = Depends(require_admin_principal) # Admin only
):
    """Create a new user. Requires admin privileges."""
    existing_user = user_crud["get_by_username"](db, username=user_in.username)
    if existing_user: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    try:
        # crud_user create_user now handles role_name to find/assign role_id
        user = user_crud["create"](db, user_in=user_in)
    except ValueError as ve: # Raised by CRUD if role not found
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    return user

@router.get("/", response_model=List[UserPublic])
async def list_users_endpoint(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    admin_principal: Dict[str, Any] = Depends(require_admin_principal) # Admin only
):
    """List users. Requires admin privileges."""
    users = user_crud["get_multi"](db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=UserPublic)
async def get_user_endpoint(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_principal: Dict[str, Any] = Depends(get_current_principal)
):
    """Get user details. Admin can get any user. Regular users can only get their own (if ID matches principal['id'])."""
    if current_principal["role"] != ROLE_ADMIN and str(user_id) != current_principal["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user")
    user = get_user_or_404(db, user_id=user_id)
    return user

@router.put("/{user_id}", response_model=UserPublic)
async def update_user_endpoint(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    admin_principal: Dict[str, Any] = Depends(require_admin_principal) # Admin only for now
):
    """Update user details (username, is_active, role_name). Admin only."""
    # More granular permissions could allow users to update some of their own info.
    user_to_update = get_user_or_404(db, user_id=user_id)
    if user_in.username and user_in.username != user_to_update.username:
        existing_user = user_crud["get_by_username"](db, username=user_in.username)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    try:
        updated_user = user_crud["update"](db, user_obj=user_to_update, user_in=user_in)
    except ValueError as ve: # Raised by CRUD if role not found
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    return updated_user

@router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_password_endpoint(
    user_id: uuid.UUID,
    password_data: UserPasswordUpdate, # For user updating their own password
    # admin_password_data: AdminUserPasswordUpdate, # Alternative for admin
    db: Session = Depends(get_db),
    current_principal: Dict[str, Any] = Depends(get_current_principal)
):
    """Update a user's password. User can update their own. Admin can update any (TODO: implement admin part if needed)."""
    user_to_update = get_user_or_404(db, user_id=user_id)

    if str(user_id) == current_principal["id"]:
        # User updating their own password
        if current_principal["auth_method"] != "basic":
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password update only supported for basic auth users.")
        if not verify_password(password_data.current_password, user_to_update.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")
        user_crud["update_password"](db, user_obj=user_to_update, new_password=password_data.new_password)
    elif current_principal["role"] == ROLE_ADMIN:
        # Admin updating user's password - requires AdminUserPasswordUpdate schema
        # For simplicity, this example reuses UserPasswordUpdate and omits current_password check for admin.
        # In a real app, you'd use a different Pydantic model for admin (AdminUserPasswordUpdate)
        # and pass that to this endpoint, or have a separate endpoint.
        # For now, let's assume admin needs to provide new_password from AdminUserPasswordUpdate if we were to use it.
        # This endpoint expects UserPasswordUpdate, so admin path is not fully distinct here yet.
        # To make it distinct, you'd check the input schema type or have a separate endpoint/schema.
        # For now, admin cannot use this endpoint to change others' passwords without their current password.
        # This should be changed to use AdminUserPasswordUpdate for admin.
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Admin password update for other users not fully implemented here. Use a dedicated schema or endpoint.")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user's password")
    return

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin_principal: Dict[str, Any] = Depends(require_admin_principal) # Admin only
):
    """Delete a user. Requires admin privileges."""
    user_to_delete = get_user_or_404(db, user_id=user_id)
    if user_to_delete.username == admin_principal["username"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin users cannot delete themselves via this endpoint.")
    user_crud["delete"](db, user_id=user_id)
    return
