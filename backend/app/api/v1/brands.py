from fastapi import APIRouter, status

from app.schemas import BrandCreate, BrandRead
from app.services.fake_catalog import fake_catalog_store

router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def create_brand(payload: BrandCreate) -> BrandRead:
    return fake_catalog_store.create_brand(payload)


@router.get("", response_model=list[BrandRead])
async def list_brands() -> list[BrandRead]:
    return fake_catalog_store.list_brands()

