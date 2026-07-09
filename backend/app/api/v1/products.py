from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.schemas import ProductRead
from app.services.fake_catalog import fake_catalog_store
from app.services.products import ProductCatalogService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductRead])
async def list_products(
    session: AsyncSession = Depends(get_session),
) -> list[ProductRead]:
    try:
        products = await ProductCatalogService(session).list_products()
    except Exception:
        return fake_catalog_store.list_products()

    return products or fake_catalog_store.list_products()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProductRead:
    try:
        product = await ProductCatalogService(session).get_product(product_id)
    except Exception:
        product = fake_catalog_store.get_product(product_id)

    if product is None:
        product = fake_catalog_store.get_product(product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product
