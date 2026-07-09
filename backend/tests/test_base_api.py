import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_and_list_brands(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/brands",
        json={"name": "Test Brand", "shopify_domain": "test.myshopify.com"},
    )
    list_response = await client.get("/api/v1/brands")

    assert create_response.status_code == 201
    assert create_response.json()["slug"] == "test-brand"
    assert list_response.status_code == 200
    assert any(brand["name"] == "PelleVista" for brand in list_response.json())
    assert any(brand["name"] == "Test Brand" for brand in list_response.json())


@pytest.mark.asyncio
async def test_list_seed_products(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products")
    product_titles = {product["title"] for product in response.json()}

    assert response.status_code == 200
    assert product_titles == {
        "Black Oxford Red Sole Shoes",
        "Brown Monk Strap Leather Shoes",
        "Oxblood Wholecut Oxford Shoes",
        "Black Loafers Red Sole",
    }


@pytest.mark.asyncio
async def test_get_seed_product(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products/1")

    assert response.status_code == 200
    assert response.json()["title"] == "Black Oxford Red Sole Shoes"


@pytest.mark.asyncio
async def test_get_missing_product(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


@pytest.mark.asyncio
async def test_list_seed_product_images(client: AsyncClient) -> None:
    response = await client.get("/api/v1/product-images")

    assert response.status_code == 200
    assert len(response.json()) == 4


@pytest.mark.asyncio
async def test_filter_seed_product_images_by_product_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/product-images", params={"product_id": 2})

    assert response.status_code == 200
    assert response.json()[0]["alt_text"] == "Brown Monk Strap Leather Shoes"
