from sqlalchemy.orm import Session
from typing import Optional, List, Union, Dict, Any
import uuid

from app.models.user_models import User
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.auth.security import get_password_hash

def get_user(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user_in: UserCreate) -> User:
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        is_active=user_in.is_active if user_in.is_active is not None else True,
        is_superuser=user_in.is_superuser if user_in.is_superuser is not None else False,
        role_id=user_in.role_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_obj: User, user_in: Union[UserUpdate, Dict[str, Any]]) -> Optional[User]:
    if isinstance(user_in, dict):
        update_data = user_in
    else:
        update_data = user_in.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        user_obj.hashed_password = hashed_password
        del update_data["password"]

    for field, value in update_data.items():
        setattr(user_obj, field, value)

    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

def delete_user(db: Session, user_id: uuid.UUID) -> Optional[User]:
    user_obj = db.query(User).filter(User.id == user_id).first()
    if user_obj:
        db.delete(user_obj)
        db.commit()
    return user_obj

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    from app.auth.security import verify_password
    user_obj = get_user_by_username(db, username=username) # Renamed user to user_obj
    if not user_obj:
        return None
    if not verify_password(password, user_obj.hashed_password):
        return None
    return user_obj

user = {
    "get": get_user,
    "get_by_username": get_user_by_username,
    "get_by_email": get_user_by_email,
    "get_multi": get_users,
    "create": create_user,
    "update": update_user,
    "delete": delete_user,
    "authenticate": authenticate_user,
}
