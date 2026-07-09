from dataclasses import dataclass
from typing import Any

import pytest

from app.models import PlatformPost, PostAnalytics, Product
from app.services.publishers.pinterest import PinterestPublisher, PinterestPublishError


@dataclass
class FakeResponse:
    payload: dict[str, Any]
    headers: dict[str, str] | None = None
    status_code: int = 200

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakePinterestHttpClient:
    def __init__(self, media_type: str = "image/jpeg") -> None:
        self.media_type = media_type
        self.head_urls: list[str] = []
        self.get_calls: list[dict[str, Any]] = []
        self.post_calls: list[dict[str, Any]] = []

    async def head(self, url: str) -> FakeResponse:
        self.head_urls.append(url)
        return FakeResponse(payload={}, headers={"content-type": self.media_type})

    async def get(self, url: str, headers: dict[str, str]) -> FakeResponse:
        self.get_calls.append({"url": url, "headers": headers})
        return FakeResponse(
            payload={
                "items": [
                    {"id": "board-1", "name": "Style Ideas"},
                    {"id": "board-2", "name": "PelleVista Shoes"},
                ],
            },
        )

    async def post(
        self,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> FakeResponse:
        self.post_calls.append({"url": url, "headers": headers, "json": json})
        return FakeResponse(
            payload={
                "id": "pin-789",
                "url": "https://www.pinterest.com/pin/pin-789/",
            },
        )


class FakePinterestSession:
    def __init__(self, post: PlatformPost, product: Product) -> None:
        self.post = post
        self.product = product
        self.commits = 0
        self.analytics: list[PostAnalytics] = []

    async def get(self, model: type[object], entity_id: int) -> object | None:
        if model is PlatformPost and entity_id == self.post.id:
            return self.post
        if model is Product and entity_id == self.product.id:
            return self.product

        return None

    def add(self, model: object) -> None:
        if isinstance(model, PostAnalytics):
            self.analytics.append(model)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, model: object) -> None:
        return None


def _product() -> Product:
    return Product(
        id=10,
        brand_id=1,
        shopify_product_id="gid://shopify/Product/10",
        handle="black-oxford-red-sole-shoes",
        title="Black Oxford Red Sole Shoes",
        vendor="PelleVista",
        product_type="Dress Shoes",
    )


def _pinterest_post(**overrides: object) -> PlatformPost:
    values = {
        "id": 1,
        "content_idea_id": 1,
        "product_id": 10,
        "platform": "pinterest",
        "status": "publishing",
        "draft_caption": (
            "Title: Handcrafted Men's Black Oxford Shoes\n\n"
            "Description:\n"
            "Premium handcrafted men's leather oxford shoes for formal outfits, "
            "weddings, office wear, and luxury style."
        ),
        "draft_media_url": "https://cdn.pellevista.example/pinterest-pin.jpg",
    }
    values.update(overrides)
    return PlatformPost(**values)


@pytest.mark.asyncio
async def test_pinterest_publisher_creates_image_pin_and_marks_published() -> None:
    post = _pinterest_post()
    product = _product()
    session = FakePinterestSession(post=post, product=product)
    client = FakePinterestHttpClient()

    published_post = await PinterestPublisher(
        session=session,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
        access_token="pin-token",
        api_base_url="https://api.pinterest.test/v5",
        board_id="board-123",
        public_pin_base_url="https://pinterest.test/pin",
        store_base_url="https://pellevista.com",
    ).publish_post(1)

    assert client.head_urls == ["https://cdn.pellevista.example/pinterest-pin.jpg"]
    assert client.get_calls == []
    assert client.post_calls == [
        {
            "url": "https://api.pinterest.test/v5/pins",
            "headers": {
                "Authorization": "Bearer pin-token",
                "Content-Type": "application/json",
            },
            "json": {
                "board_id": "board-123",
                "title": "Handcrafted Men's Black Oxford Shoes",
                "description": (
                    "Premium handcrafted men's leather oxford shoes for formal "
                    "outfits, weddings, office wear, and luxury style."
                ),
                "link": "https://pellevista.com/products/black-oxford-red-sole-shoes",
                "alt_text": "Handcrafted Men's Black Oxford Shoes",
                "media_source": {
                    "source_type": "image_url",
                    "url": "https://cdn.pellevista.example/pinterest-pin.jpg",
                },
            },
        },
    ]
    assert published_post.status == "published"
    assert published_post.published_at is not None
    assert published_post.external_post_id == "pin-789"
    assert published_post.external_post_url == "https://www.pinterest.com/pin/pin-789/"
    assert published_post.publish_error is None
    assert [snapshot.collection_label for snapshot in session.analytics] == [
        "published",
        "1h",
        "24h",
        "72h",
        "7d",
    ]


@pytest.mark.asyncio
async def test_pinterest_publisher_selects_configured_board_name() -> None:
    post = _pinterest_post()
    product = _product()
    session = FakePinterestSession(post=post, product=product)
    client = FakePinterestHttpClient()

    await PinterestPublisher(
        session=session,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
        access_token="pin-token",
        api_base_url="https://api.pinterest.test/v5",
        board_name="PelleVista Shoes",
        store_base_url="https://pellevista.com",
    ).publish_post(1)

    assert client.get_calls == [
        {
            "url": "https://api.pinterest.test/v5/boards",
            "headers": {
                "Authorization": "Bearer pin-token",
                "Content-Type": "application/json",
            },
        },
    ]
    assert client.post_calls[0]["json"]["board_id"] == "board-2"


@pytest.mark.asyncio
async def test_pinterest_publisher_rejects_video_media_in_v1_and_marks_failed() -> None:
    post = _pinterest_post(draft_media_url="https://cdn.pellevista.example/pin.mp4")
    product = _product()
    session = FakePinterestSession(post=post, product=product)
    client = FakePinterestHttpClient(media_type="video/mp4")

    with pytest.raises(PinterestPublishError, match="Only image media is supported"):
        await PinterestPublisher(
            session=session,  # type: ignore[arg-type]
            client=client,  # type: ignore[arg-type]
            access_token="pin-token",
            board_id="board-123",
            store_base_url="https://pellevista.com",
        ).publish_post(1)

    assert post.status == "failed"
    assert post.publish_error == (
        "Only image media is supported for Pinterest publishing in v1."
    )
    assert client.post_calls == []


@pytest.mark.asyncio
async def test_pinterest_publisher_requires_product_destination_url() -> None:
    post = _pinterest_post()
    product = _product()
    session = FakePinterestSession(post=post, product=product)
    client = FakePinterestHttpClient()

    with pytest.raises(RuntimeError, match="PELLEVISTA_STORE_BASE_URL is required"):
        await PinterestPublisher(
            session=session,  # type: ignore[arg-type]
            client=client,  # type: ignore[arg-type]
            access_token="pin-token",
            board_id="board-123",
            store_base_url="",
        ).publish_post(1)

    assert post.status == "failed"
    assert post.publish_error == "PELLEVISTA_STORE_BASE_URL is required."
