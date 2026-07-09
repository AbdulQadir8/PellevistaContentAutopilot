from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Product
from app.services.shopify.product_sync import ProductSyncService


@pytest.fixture
def product_sync_service() -> ProductSyncService:
    return object.__new__(ProductSyncService)


@pytest.mark.asyncio
async def test_sync_status_endpoint() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/shopify/sync-status")

    assert response.status_code == 200
    assert response.json()["status"] in {"idle", "running", "completed", "failed"}


@pytest.mark.asyncio
async def test_shopify_sync_requires_credentials() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/api/v1/shopify/sync")

    assert response.status_code == 400
    assert "SHOPIFY_SHOP_DOMAIN" in response.json()["detail"]


def test_eligibility_requires_active_image_price_stock_and_no_recent_post(
    product_sync_service: ProductSyncService,
) -> None:
    product = Product(
        brand_id=1,
        shopify_product_id="gid://shopify/Product/1",
        handle="black-oxford-red-sole-shoes",
        title="Black Oxford Red Sole Shoes",
        status="active",
        price="189.00",
        available_for_sale=True,
        has_image=True,
        last_posted_at=None,
    )

    assert product_sync_service._is_eligible(product)

    product.last_posted_at = datetime.now(UTC) - timedelta(days=1)

    assert not product_sync_service._is_eligible(product)


def test_priority_score_rewards_sync_ready_products(
    product_sync_service: ProductSyncService,
) -> None:
    product = Product(
        brand_id=1,
        shopify_product_id="gid://shopify/Product/1",
        handle="black-oxford-red-sole-shoes",
        title="Black Oxford Red Sole Shoes",
        status="active",
        price="189.00",
        available_for_sale=True,
        has_image=True,
        tags="oxford,black,red-sole",
    )

    assert product_sync_service._priority_score(product) == 96

