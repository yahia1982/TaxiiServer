from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.crud.crud_user import user_crud
from app.models.user_models import User as UserModel
from app.auth.apikey import validate_api_key # Import the placeholder validator

# --- Define Security Schemes ---
basic_auth_scheme = HTTPBasic(auto_error=False, description="HTTP Basic Authentication")

# --- Role Name Constants ---
ROLE_ADMIN = "admin"
ROLE_LITE_FEED = "lite_feed_user"
ROLE_FULL_ACCESS = "full_access_user"
ROLE_DEFAULT_APIKEY = "default_apikey_role"
ROLE_DEFAULT_USER = "default_user_role"

async def get_current_principal(
    api_key_principal: Optional[Dict[str, Any]] = Depends(validate_api_key),
    basic_creds: Optional[HTTPBasicCredentials] = Security(basic_auth_scheme),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    if api_key_principal:
        return {
            "id": api_key_principal.get("user_id", "unknown_apikey_user"),
            "username": api_key_principal.get("username", "unknown_apikey_user"),
            "role": api_key_principal.get("role", ROLE_DEFAULT_APIKEY),
            "auth_method": "apikey"
        }
    if basic_creds:
        user_db_obj: Optional[UserModel] = user_crud["authenticate"](db, username=basic_creds.username, password=basic_creds.password)
        if user_db_obj:
            if not user_db_obj.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
            return {
                "id": str(user_db_obj.id),
                "username": user_db_obj.username,
                "role": user_db_obj.role.name if user_db_obj.role else ROLE_DEFAULT_USER,
                "auth_method": "basic"
            }
    headers = {"WWW-Authenticate": "Basic realm=\"TAXII Server\""}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers=headers)

async def require_admin_principal(principal: Dict[str, Any] = Depends(get_current_principal)) -> Dict[str, Any]:
    if principal.get("role") != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required")
    return principal
