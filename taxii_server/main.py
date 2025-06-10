from contextlib import asynccontextmanager

from bfore_auth import set_jwks_keys, validate_token
from fastapi import FastAPI, Depends
from app.core.config import settings
from app.api.api_v1_router import api_router as v1_api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="BforeAI TAXII Server",
    lifespan=lifespan,
    docs_url="/taxii/docs",
    redoc_url="/taxii/redoc",
    openapi_url="/taxi/openapi.json",
)

app.include_router(
    v1_api_router
)  # , dependencies=[Depends(validate_token)])#, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}. See {settings.API_V1_STR}/docs for API docs."
    }


# Example for init_db, commented out by default
# from app.core.database import SessionLocal
# from app.models import *
# from app.crud import user as crud_user, role as crud_role, api_root as crud_api_root
# from app.schemas.user_schemas import UserCreate, RoleCreate
# from app.core.config import settings
# import uuid

# def init_db_command():
#     db = SessionLocal()
#     try:
#         default_role_name = "default_user"
#         admin_role_name = "admin"
#         if not crud_role.role['get_by_name'](db, name=admin_role_name):
#             crud_role.role['create'](db, role_in=RoleCreate(name=admin_role_name, description="Administrator"))
#             print(f"Role '{admin_role_name}' created.")
#         if not crud_role.role['get_by_name'](db, name=default_role_name):
#             crud_role.role['create'](db, role_in=RoleCreate(name=default_role_name, description="Default User Role"))
#             print(f"Role '{default_role_name}' created.")
#         admin_role_obj = crud_role.role['get_by_name'](db, name=admin_role_name)
#         if admin_role_obj and not crud_user.user['get_by_username'](db, username=settings.FIRST_SUPERUSER_USERNAME):
#             user_in = UserCreate(username=settings.FIRST_SUPERUSER_USERNAME, email=settings.FIRST_SUPERUSER_EMAIL, password=settings.FIRST_SUPERUSER_PASSWORD, role_id=admin_role_obj.id, is_superuser=True, is_active=True)
#             crud_user.user['create'](db, user_in=user_in)
#             print(f"Superuser '{settings.FIRST_SUPERUSER_USERNAME}' created.")
#         if not crud_api_root.api_root['get_multi'](db, limit=1):
#             crud_api_root.api_root['create'](db, title="Default API Root", description="A default TAXII API root.", max_content_length=10485760)
#             print(f"Default API Root created.")
#         print("Database initialization complete.")
#     finally: db.close()

# @app.on_event("startup")
# async def on_startup():
#     # init_db_command()
#     pass
