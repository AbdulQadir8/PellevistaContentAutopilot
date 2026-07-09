from datetime import date
from io import BytesIO
from uuid import UUID

import pytest
from PIL import Image

from app.core.config import settings
from app.services.assets import AssetStorageService, DownloadedAsset


@pytest.fixture
def configured_storage(monkeypatch: pytest.MonkeyPatch) -> AssetStorageService:
    monkeypatch.setattr(settings, "asset_bucket_name", "pellevista-assets")
    monkeypatch.setattr(settings, "asset_public_base_url", "https://cdn.example.com")
    return AssetStorageService()


def test_build_storage_key_matches_brand_product_platform_date_path(
    configured_storage: AssetStorageService,
) -> None:
    key = configured_storage.build_storage_key(
        brand_slug="pellevista",
        product_id=42,
        platform="instagram",
        asset_date=date(2026, 7, 9),
        asset_id=UUID("00000000-0000-0000-0000-000000000123"),
        extension="mp4",
    )

    assert key == (
        "brands/pellevista/products/42/instagram/2026-07-09/"
        "00000000-0000-0000-0000-000000000123.mp4"
    )


def test_get_public_url_uses_configured_public_base(
    configured_storage: AssetStorageService,
) -> None:
    assert configured_storage.get_public_url("/brands/pellevista/file.jpg") == (
        "https://cdn.example.com/brands/pellevista/file.jpg"
    )


@pytest.mark.asyncio
async def test_upload_file_writes_to_s3_key(
    configured_storage: AssetStorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded: dict[str, object] = {}

    def fake_upload_bytes(
        key: str,
        content: bytes,
        mime_type: str | None,
    ) -> None:
        uploaded["key"] = key
        uploaded["content"] = content
        uploaded["mime_type"] = mime_type

    monkeypatch.setattr(configured_storage, "_upload_bytes", fake_upload_bytes)

    result = await configured_storage.upload_file(
        content=b"image-bytes",
        storage_key="/brands/pellevista/file.jpg",
        mime_type="image/jpeg",
    )

    assert uploaded == {
        "key": "brands/pellevista/file.jpg",
        "content": b"image-bytes",
        "mime_type": "image/jpeg",
    }
    assert result.storage_url == "https://cdn.example.com/brands/pellevista/file.jpg"
    assert result.file_size_bytes == 11


@pytest.mark.asyncio
async def test_create_thumbnail_uploads_jpeg_thumbnail(
    configured_storage: AssetStorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded: dict[str, object] = {}
    image = Image.new("RGB", (1000, 800), color=(20, 40, 60))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    def fake_upload_bytes(
        key: str,
        content: bytes,
        mime_type: str | None,
    ) -> None:
        uploaded["key"] = key
        uploaded["mime_type"] = mime_type
        uploaded["size"] = len(content)

    monkeypatch.setattr(configured_storage, "_upload_bytes", fake_upload_bytes)

    thumbnail = await configured_storage.create_thumbnail(
        downloaded_asset=DownloadedAsset(
            source_url="https://higgsfield.example/result.png",
            content=buffer.getvalue(),
            mime_type="image/png",
        ),
        storage_key="brands/pellevista/products/42/instagram/2026-07-09/asset.thumbnail.jpg",
    )

    assert thumbnail is not None
    assert uploaded["key"] == (
        "brands/pellevista/products/42/instagram/2026-07-09/"
        "asset.thumbnail.jpg"
    )
    assert uploaded["mime_type"] == "image/jpeg"
    assert isinstance(uploaded["size"], int)
    assert uploaded["size"] > 0


@pytest.mark.asyncio
async def test_create_thumbnail_skips_video_assets(
    configured_storage: AssetStorageService,
) -> None:
    thumbnail = await configured_storage.create_thumbnail(
        downloaded_asset=DownloadedAsset(
            source_url="https://higgsfield.example/result.mp4",
            content=b"video",
            mime_type="video/mp4",
        ),
        storage_key="brands/pellevista/products/42/instagram/2026-07-09/asset.thumbnail.jpg",
    )

    assert thumbnail is None
