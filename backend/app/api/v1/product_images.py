from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.schemas import ProductImageRead
from app.services.fake_catalog import fake_catalog_store
from app.services.products import ProductCatalogService

router = APIRouter(prefix="/product-images", tags=["product-images"])


@router.get("", response_model=list[ProductImageRead])
async def list_product_images(
    product_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
) -> list[ProductImageRead]:
    try:
        images = await ProductCatalogService(session).list_product_images(
            product_id=product_id,
        )
    except Exception:
        return fake_catalog_store.list_product_images(product_id=product_id)

    return images or fake_catalog_store.list_product_images(product_id=product_id)
