from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials, APIKeyHeader # APIKeyHeader might be from apikey.py
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.crud.crud_user import user_crud  # Assuming user_crud dict
from app.models.user_models import User as UserModel # For DB user object
from app.auth.apikey import validate_api_key # Import the placeholder validator

# --- Define Security Schemes ---
# auto_error=False allows our combined dependency to try multiple auth methods
basic_auth_scheme = HTTPBasic(auto_error=False, description="HTTP Basic Authentication")
# The APIKeyHeader scheme is defined in apikey.py and used by validate_api_key

# --- Role Name Constants (Consider moving to a config or enums) ---
ROLE_ADMIN = "admin"
ROLE_LITE_FEED = "lite_feed_user"
ROLE_FULL_ACCESS = "full_access_user"
ROLE_DEFAULT_APIKEY = "default_apikey_role" # Default role from placeholder API key validation
ROLE_DEFAULT_USER = "default_user_role" # Fallback if user has no role in DB (should be prevented)

async def get_current_principal(
    # Try API Key first
    api_key_principal: Optional[Dict[str, Any]] = Depends(validate_api_key),
    # Then try HTTP Basic Auth
    basic_creds: Optional[HTTPBasicCredentials] = Security(basic_auth_scheme),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Attempts to authenticate user via API Key or HTTP Basic Auth.
    Returns a principal dictionary: {'id': str, 'username': str, 'role': str, 'auth_method': str}
    Raises HTTPException(401) if neither method succeeds.
    """

    if api_key_principal: # API Key was provided and validated by placeholder
        # Ensure the principal from API key has a consistent structure
        return {
            "id": api_key_principal.get("user_id", "unknown_apikey_user"),
            "username": api_key_principal.get("username", "unknown_apikey_user"),
            "role": api_key_principal.get("role", ROLE_DEFAULT_APIKEY),
            "auth_method": "apikey"
        }

    if basic_creds: # HTTP Basic credentials provided
        user_db_obj: Optional[UserModel] = user_crud["authenticate"](db, username=basic_creds.username, password=basic_creds.password)
        if user_db_obj:
            if not user_db_obj.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
            return {
                "id": str(user_db_obj.id),
                "username": user_db_obj.username,
                "role": user_db_obj.role.name if user_db_obj.role else ROLE_DEFAULT_USER,
                "auth_method": "basic"
                # Optionally include the raw user_db_obj if needed by some downstream logic, but generally avoid
                # "db_user_obj": user_db_obj
            }
        # If basic_creds were provided but authentication failed, fall through to 401

    # If neither API key worked nor Basic Auth credentials were provided / were valid
    headers = {"WWW-Authenticate": "Basic realm=\"TAXII Server\""} # Challenge with Basic
    # If you want to indicate API key is also an option, the WWW-Authenticate gets more complex.
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers=headers)

async def require_admin_principal(principal: Dict[str, Any] = Depends(get_current_principal)) -> Dict[str, Any]:
    """Ensures the authenticated principal has an admin role."""
    # In User model, admin status could be via role name 'admin' or an 'is_admin' boolean.
    # Here, we check the 'role' field in the principal dict.
    if principal.get("role") != ROLE_ADMIN:
        # Check if the user is admin via is_admin flag from API Key if role is not admin
        # This part depends on the structure of api_key_principal
        # For now, placeholder logic: if auth_method is apikey and a hypothetical is_admin flag was true
        # if principal.get("auth_method") == "apikey" and principal.get("is_admin", False):
        #    return principal
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required")
    return principal

# You might want a general 'require_authenticated_principal' that just ensures get_current_principal didn't raise 401
# but usually get_current_principal itself is used directly on endpoints, as it raises 401 if no auth.
