from pydantic import BaseModel
from typing import Optional, List
import uuid

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None # Subject (username or user ID)
    # Add any other fields you expect in the token payload (e.g., scopes, user_id)

# Re-define TokenData here or ensure it's consistently used from jwt.py
# For clarity, let's define it here as well if it's used externally by schemas
class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []
    user_id: Optional[uuid.UUID] = None # If you plan to include user_id in token

# Schema for user login
class UserLogin(BaseModel):
    username: str
    password: str
