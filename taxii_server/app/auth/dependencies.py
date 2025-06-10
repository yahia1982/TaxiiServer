# This file now primarily re-exports dependencies from bfore_auth
# Or defines any application-specific wrappers if needed.

from fastapi import (
    Depends,
    HTTPException,
    status,
)  # Keep for potential custom error handling

# Assuming bfore_auth.get_current_user is a FastAPI dependency that provides bfore_auth.types.User
# It should handle token validation and user object creation.
from bfore_auth import get_current_user, types as bfore_types  # Stubbing this import

# Re-export for convenience in other modules if desired, though direct import is also fine.
# def get_current_active_user(...): -> This logic (checking is_active) might move or change
# based on bfore_types.User structure.
# For now, the main dependency is directly get_current_user from bfore_auth.

# Placeholder for TokenData if needed by bfore_auth or internal JWT parsing (likely not needed now)
# from app.schemas.auth_schemas import TokenData

# The oauth2_scheme is removed as token URL is external / handled by bfore_auth
