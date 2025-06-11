from sqlalchemy.orm import Session
from typing import Optional, List, Union, Dict, Any
import uuid

from app.models.user_models import User, Role
from app.schemas.user_schemas import UserCreate, UserUpdate # UserPasswordUpdate handled by service logic
from app.auth.security import get_password_hash, verify_password # Assuming security.py will be re-created or exists
from .crud_role import get_role_by_name # For assigning role by name

def get_user(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user_in: UserCreate) -> User:
    hashed_password = get_password_hash(user_in.password)
    db_user = User(username=user_in.username, hashed_password=hashed_password, is_active=True)
    if user_in.role_name:
        role_obj = get_role_by_name(db, name=user_in.role_name)
        if not role_obj: raise ValueError(f"Role '{user_in.role_name}' not found") # Corrected quote in f-string
        db_user.role_id = role_obj.id
    db.add(db_user); db.commit(); db.refresh(db_user)
    return db_user

def update_user(db: Session, user_obj: User, user_in: Union[UserUpdate, Dict[str, Any]]) -> Optional[User]:
    update_data = user_in if isinstance(user_in, dict) else user_in.model_dump(exclude_unset=True)
    if "role_name" in update_data:
        if update_data["role_name"] is None:
            user_obj.role_id = None
        else:
            role_obj = get_role_by_name(db, name=update_data["role_name"])
            if not role_obj: raise ValueError(f"Role '{update_data['role_name']}' not found") # Corrected quote in f-string
            user_obj.role_id = role_obj.id
        del update_data["role_name"]
    for field, value in update_data.items(): setattr(user_obj, field, value)
    db.add(user_obj); db.commit(); db.refresh(user_obj)
    return user_obj

def update_password(db: Session, user_obj: User, new_password: str) -> User:
    user_obj.hashed_password = get_password_hash(new_password)
    db.add(user_obj); db.commit(); db.refresh(user_obj)
    return user_obj

def delete_user(db: Session, user_id: uuid.UUID) -> Optional[User]:
    user_obj = db.query(User).get(user_id) # Changed to .get() for primary key lookup
    if user_obj: db.delete(user_obj); db.commit()
    return user_obj

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username=username)
    if not user: return None
    if not verify_password(password, user.hashed_password): return None
    return user

user_crud = { "get": get_user, "get_by_username": get_user_by_username, "get_multi": get_users, "create": create_user, "update": update_user, "delete": delete_user, "authenticate": authenticate_user, "update_password": update_password }
