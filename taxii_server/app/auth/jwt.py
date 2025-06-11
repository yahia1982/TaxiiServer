from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any

from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

class TokenData(BaseModel):
    username: Optional[str] = None
    # Add any other data you want to store in the token, e.g., user_id, roles
    sub: Optional[str] = None # 'sub' is standard for subject (usually username or user_id)
    scopes: list[str] = [] # For more granular permissions


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# This function will be used by dependency to decode token and get user
def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
