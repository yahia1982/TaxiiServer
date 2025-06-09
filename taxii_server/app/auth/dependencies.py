from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user_models import User, Role # Assuming User model is defined
from app.schemas.auth_schemas import TokenData # Will create this schema later
from app.crud import user as crud_user_module

# OAuth2PasswordBearer will be used for token URL, adjust if your token URL is different
# This points to an endpoint that clients will use to get the token.
# We will create this endpoint (e.g., /token, /auth/login) later.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login", # Example token URL
    scopes={"read": "Read access", "write": "Write access"} # Example scopes
)

async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username) # May add scopes here later if in token
    except (JWTError, ValidationError):
        raise credentials_exception

    # Replace with actual database call once CRUD is available
    # user = get_user_by_username(db, username=token_data.username)
    user = crud_user_module.user["get_by_username"](db, username=token_data.username) # Placeholder DB call

    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user_from_token)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# Placeholder for role-based dependency
# This is a simplified version. A more robust one would check specific permissions
# associated with roles or use the SecurityScopes feature of FastAPI.
class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)):
        if not current_user.role: # Check if user has a role assigned
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no role assigned."
            )
        if current_user.role.name not in self.allowed_roles:
            # If current_user.is_superuser is a concept, you might bypass here:
            # if current_user.is_superuser:
            #     return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role.name}' is not authorized for this resource. Required roles: {self.allowed_roles}"
            )
        # Optionally, return the user or True if access is granted
        return current_user

# Example usage for an endpoint:
# @app.get("/users/me", dependencies=[Depends(RoleChecker(["admin", "user"]))])
# async def read_users_me(current_user: User = Depends(get_current_user_from_token)):
#     return current_user
