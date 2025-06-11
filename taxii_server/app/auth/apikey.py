from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from typing import Optional, Dict, Any

# Define the API Key Header
# auto_error=False means if the key is missing or invalid, FastAPI won't automatically
# raise an error. Instead, our dependency will return None, allowing us to try other auth methods.
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False, description="API Key for authentication")

async def validate_api_key(api_key: Optional[str] = Security(api_key_header_scheme)) -> Optional[Dict[str, Any]]:
    """Placeholder for API Key Validation.
    This function should be replaced with actual logic to validate the API key
    against your external storage or system.
    If valid, it should return a dictionary with user information like:
    {'user_id': 'some_id', 'username': 'some_username', 'role': 'user_role'}
    """
    if not api_key:
        return None # No API key provided

    # --- Placeholder Logic ---
    # Replace this with your actual API key validation
    if api_key == "TEST_API_KEY_ADMIN":
        # Example: A test key that grants admin role
        return {"user_id": "apikey_admin_001", "username": "apikey_admin", "role": "admin", "auth_method": "apikey"}
    elif api_key == "TEST_API_KEY_LITE":
        # Example: A test key that grants a 'lite_feed_user' role
        return {"user_id": "apikey_lite_002", "username": "apikey_lite_user", "role": "lite_feed_user", "auth_method": "apikey"}
    elif api_key == "TEST_API_KEY_FULL":
        # Example: A test key that grants a 'full_access_user' role
        return {"user_id": "apikey_full_003", "username": "apikey_full_user", "role": "full_access_user", "auth_method": "apikey"}
    # --- End Placeholder Logic ---

    # If key is not one of the test keys, consider it invalid for this placeholder
    # In real implementation, you'd query your system.
    # To simulate a key that was found but tied to no specific permissions or an error:
    # if api_key == INVALID_BUT_KNOWN_KEY:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=API Key recognized but lacks permissions)

    return None # Key not recognized by placeholder logic
