from fastapi import HTTPException, status
from app.models.taxii_models import Collection as CollectionModel
from bfore_auth import types as bfore_types  # Use bfore_types.User

from app.schemas.taxii_schemas import UserScope


def check_read_permission(collection: CollectionModel, user: bfore_types.User):
    if collection.is_public_readable:
        return True
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    # Use user.is_admin and user.scopes from bfore_types.User
    if user.is_admin:
        return True
    # Example scope check, adapt as needed
    if any(s in user.scopes for s in [scope.value for scope in UserScope]):
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User lacks read permission for this collection.",
    )


def check_write_permission(collection: CollectionModel, user: bfore_types.User):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    if user.is_admin:
        return True
    # Example scope check for write
    if any(s in user.scopes for s in [UserScope.SYS_ADMIN.value]):
        return True
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User lacks write permission for this collection.",
    )
