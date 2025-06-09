from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import uuid
from datetime import datetime

# Role Schemas
class RoleBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    description: Optional[str] = None

class RoleInDBBase(RoleBase):
    id: uuid.UUID

    class Config:
        from_attributes = True # Replaces orm_mode = True in Pydantic v2

class Role(RoleInDBBase):
    pass

# User Schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role_id: Optional[uuid.UUID] = None # Allow creating user with a role

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role_id: Optional[uuid.UUID] = None
    password: Optional[str] = Field(None, min_length=8)

class UserInDBBase(UserBase):
    id: uuid.UUID
    role: Optional[Role] = None # Display role information
    created_at: datetime
    # updated_at is often not included in responses unless specifically needed

    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass # Full user representation

class UserPublic(BaseModel): # For public display, no sensitive info
    id: uuid.UUID
    username: str
    role_name: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, user_orm):
        return cls(
            id=user_orm.id,
            username=user_orm.username,
            role_name=user_orm.role.name if user_orm.role else None
        )
