from pydantic import BaseModel, Field # Removed EmailStr as email field was removed from User model for now
from typing import Optional, List
import uuid
from datetime import datetime

# --- Role Schemas ---
class RoleBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None

class RoleCreate(RoleBase): pass

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    description: Optional[str] = None

class RoleInDBBase(RoleBase):
    id: uuid.UUID
    class Config:
        from_attributes = True

class RolePublic(RoleInDBBase): pass # For public responses

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role_name: Optional[str] = None # Assign role by name during creation

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    is_active: Optional[bool] = None
    role_name: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    current_password: str # For self-update
    new_password: str = Field(..., min_length=8)

class AdminUserPasswordUpdate(BaseModel): # For admin updating other's password
    new_password: str = Field(..., min_length=8)

class UserInDBBase(UserBase):
    id: uuid.UUID
    is_active: bool
    role: Optional[RolePublic] = None # Embed role info
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class UserPublic(UserInDBBase): pass # For public user responses
