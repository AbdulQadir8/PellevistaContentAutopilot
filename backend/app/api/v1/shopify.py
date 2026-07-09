from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.schemas import ShopifySyncStatusRead
from app.services.shopify import ProductSyncService
from app.services.shopify.client import ShopifyConfigError
from app.services.shopify.sync_status import (
    mark_completed,
    mark_failed,
    mark_running,
    sync_status,
)

router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.post("/sync", response_model=ShopifySyncStatusRead)
async def sync_shopify(
    session: AsyncSession = Depends(get_session),
) -> ShopifySyncStatusRead:
    mark_running()

    try:
        products_synced, images_synced = await ProductSyncService(session).sync()
    except ShopifyConfigError as exc:
        mark_failed(str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        mark_failed(str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Shopify sync failed.",
        ) from exc

    mark_completed(products_synced=products_synced, images_synced=images_synced)
    return ShopifySyncStatusRead.model_validate(sync_status.as_dict())


@router.get("/sync-status", response_model=ShopifySyncStatusRead)
async def get_sync_status() -> ShopifySyncStatusRead:
    return ShopifySyncStatusRead.model_validate(sync_status.as_dict())

