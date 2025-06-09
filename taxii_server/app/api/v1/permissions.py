from fastapi import HTTPException, status
from app.models.taxii_models import Collection as CollectionModel
from app.models.user_models import User as UserModel

def check_read_permission(collection: CollectionModel, user: UserModel):
    if collection.is_public_readable:
        return True
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    if user.is_superuser:
        return True
    if user.role and user.role.name in ["admin", "publisher", "consumer", "member"]:
        return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User lacks read permission for this collection.")

def check_write_permission(collection: CollectionModel, user: UserModel):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    if user.is_superuser:
        return True
    if user.role and user.role.name in ["admin", "publisher"]:
        return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User lacks write permission for this collection.")
