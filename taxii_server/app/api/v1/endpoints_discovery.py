from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import uuid
from app.crud import crud_taxii
from app.schemas import taxii_schemas
from app.core.database import get_db

router = APIRouter()

@router.get("/", response_model=taxii_schemas.Discovery, summary="Get Server Discovery Information", tags=["Discovery"])
async def get_discovery(request: Request, db: Session = Depends(get_db)):
    api_roots_db = crud_taxii.api_root["get_multi"](db, limit=100)
    base_url = str(request.url_for('get_discovery')).rstrip('/')
    api_root_urls = []
    default_api_root_url = None
    for i, api_root_model in enumerate(api_roots_db):
        current_api_root_url = f"{base_url}/{str(api_root_model.id)}/"
        api_root_urls.append(current_api_root_url)
        if i == 0: default_api_root_url = current_api_root_url
    return taxii_schemas.Discovery(
        title="TAXII Server Discovery",
        description="Lists available TAXII API Roots.",
        default=default_api_root_url if default_api_root_url else None,
        api_roots=api_root_urls if api_root_urls else []
    )
