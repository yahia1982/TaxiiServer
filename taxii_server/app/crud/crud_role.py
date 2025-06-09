from sqlalchemy.orm import Session
from typing import Optional, List, Union, Dict, Any
import uuid

from app.models.user_models import Role
from app.schemas.user_schemas import RoleCreate, RoleUpdate

def get_role(db: Session, role_id: uuid.UUID) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()

def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    return db.query(Role).filter(Role.name == name).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100) -> List[Role]:
    return db.query(Role).offset(skip).limit(limit).all()

def create_role(db: Session, role_in: RoleCreate) -> Role: # Changed 'role' to 'role_in'
    db_role = Role(name=role_in.name, description=role_in.description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def update_role(db: Session, role_obj: Role, role_in: Union[RoleUpdate, Dict[str, Any]]) -> Optional[Role]:
    if isinstance(role_in, dict):
        update_data = role_in
    else:
        update_data = role_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(role_obj, field, value)

    db.add(role_obj)
    db.commit()
    db.refresh(role_obj)
    return role_obj

def delete_role(db: Session, role_id: uuid.UUID) -> Optional[Role]:
    role_obj = db.query(Role).filter(Role.id == role_id).first()
    if role_obj:
        db.delete(role_obj)
        db.commit()
    return role_obj

role = {
    "get": get_role,
    "get_by_name": get_role_by_name,
    "get_multi": get_roles,
    "create": create_role,
    "update": update_role,
    "delete": delete_role,
}
