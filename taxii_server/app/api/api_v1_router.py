from fastapi import APIRouter
from app.api.v1 import endpoints_auth, endpoints_discovery, endpoints_api_root
from app.api.v1 import endpoints_collection, endpoints_object, endpoints_manifest
from app.api.v1 import endpoints_user_management

api_router = APIRouter()
taxii_router = APIRouter()

taxii_router.include_router(endpoints_discovery.router, prefix="", tags=["TAXII Discovery"])
taxii_router.include_router(endpoints_api_root.router, prefix="", tags=["TAXII API Root"])
taxii_router.include_router(endpoints_collection.router, prefix="", tags=["TAXII Collection"])
taxii_router.include_router(endpoints_object.router, prefix="", tags=["TAXII Objects"])
taxii_router.include_router(endpoints_manifest.router, prefix="", tags=["TAXII Manifests"])

api_router.include_router(endpoints_auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(endpoints_user_management.router, prefix="/users", tags=["User Management"])
api_router.include_router(taxii_router, prefix="/taxii2")
