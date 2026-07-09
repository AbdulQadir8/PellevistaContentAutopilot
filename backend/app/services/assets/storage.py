import asyncio
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from uuid import UUID

import boto3
import httpx
from PIL import Image, UnidentifiedImageError

from app.core.config import settings


class AssetStorageConfigError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DownloadedAsset:
    source_url: str
    content: bytes
    mime_type: str | None

    @property
    def file_size_bytes(self) -> int:
        return len(self.content)


@dataclass(frozen=True, slots=True)
class UploadedAsset:
    storage_url: str
    storage_key: str
    mime_type: str | None
    file_size_bytes: int


@dataclass(frozen=True, slots=True)
class StoredAsset:
    source_url: str
    storage_url: str
    storage_key: str
    mime_type: str | None
    file_size_bytes: int
    thumbnail_url: str | None = None
    thumbnail_storage_key: str | None = None


class AssetStorageService:
    async def upload_generated_asset(
        self,
        source_url: str,
        brand_slug: str,
        product_id: int,
        platform: str,
        asset_date: date,
        asset_id: UUID,
        asset_type: str,
    ) -> StoredAsset:
        downloaded_asset = await self.download_remote_asset(source_url)
        storage_key = self.build_storage_key(
            brand_slug=brand_slug,
            product_id=product_id,
            platform=platform,
            asset_date=asset_date,
            asset_id=asset_id,
            extension=self.extension(asset_type=asset_type, mime_type=downloaded_asset.mime_type),
        )
        uploaded_asset = await self.upload_file(
            content=downloaded_asset.content,
            storage_key=storage_key,
            mime_type=downloaded_asset.mime_type,
        )
        thumbnail = await self.create_thumbnail(
            downloaded_asset=downloaded_asset,
            storage_key=self.thumbnail_key(storage_key),
        )

        return StoredAsset(
            source_url=source_url,
            storage_url=uploaded_asset.storage_url,
            storage_key=uploaded_asset.storage_key,
            mime_type=uploaded_asset.mime_type,
            file_size_bytes=uploaded_asset.file_size_bytes,
            thumbnail_url=thumbnail.storage_url if thumbnail else None,
            thumbnail_storage_key=thumbnail.storage_key if thumbnail else None,
        )

    async def download_remote_asset(self, source_url: str) -> DownloadedAsset:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(source_url)
            response.raise_for_status()
            return DownloadedAsset(
                source_url=source_url,
                content=response.content,
                mime_type=response.headers.get("content-type"),
            )

    async def upload_file(
        self,
        content: bytes,
        storage_key: str,
        mime_type: str | None,
    ) -> UploadedAsset:
        self.ensure_configured()
        normalized_key = self.normalize_key(storage_key)

        await asyncio.to_thread(
            self._upload_bytes,
            key=normalized_key,
            content=content,
            mime_type=mime_type,
        )

        return UploadedAsset(
            storage_url=self.get_public_url(normalized_key),
            storage_key=normalized_key,
            mime_type=mime_type,
            file_size_bytes=len(content),
        )

    async def create_thumbnail(
        self,
        downloaded_asset: DownloadedAsset,
        storage_key: str,
        size: tuple[int, int] = (512, 512),
    ) -> UploadedAsset | None:
        if not self.is_image(downloaded_asset.mime_type):
            return None

        try:
            thumbnail_content = await asyncio.to_thread(
                self._create_thumbnail_bytes,
                downloaded_asset.content,
                size,
            )
        except UnidentifiedImageError:
            return None

        return await self.upload_file(
            content=thumbnail_content,
            storage_key=storage_key,
            mime_type="image/jpeg",
        )

    def get_public_url(self, storage_key: str) -> str:
        normalized_key = self.normalize_key(storage_key)
        if settings.asset_public_base_url:
            return f"{settings.asset_public_base_url.rstrip('/')}/{normalized_key}"

        endpoint = settings.asset_bucket_endpoint_url.rstrip("/")
        if endpoint:
            return f"{endpoint}/{settings.asset_bucket_name}/{normalized_key}"

        return f"s3://{settings.asset_bucket_name}/{normalized_key}"

    def build_storage_key(
        self,
        brand_slug: str,
        product_id: int,
        platform: str,
        asset_date: date,
        asset_id: UUID,
        extension: str,
    ) -> str:
        return self.normalize_key(
            (
                f"/brands/{brand_slug}/products/{product_id}/"
                f"{platform.lower()}/{asset_date.isoformat()}/{asset_id}.{extension}"
            ),
        )

    @staticmethod
    def thumbnail_key(storage_key: str) -> str:
        base, _, _extension = storage_key.rpartition(".")
        if not base:
            base = storage_key

        return f"{base}.thumbnail.jpg"

    @staticmethod
    def normalize_key(storage_key: str) -> str:
        return storage_key.strip().lstrip("/")

    @staticmethod
    def extension(asset_type: str, mime_type: str | None) -> str:
        if mime_type:
            clean_mime = mime_type.split(";")[0].strip().lower()
            if clean_mime == "image/png":
                return "png"
            if clean_mime == "image/webp":
                return "webp"
            if clean_mime in {"image/jpeg", "image/jpg"}:
                return "jpg"
            if clean_mime == "video/mp4":
                return "mp4"

        return "mp4" if asset_type == "video" else "jpg"

    @staticmethod
    def is_image(mime_type: str | None) -> bool:
        return bool(mime_type and mime_type.split(";")[0].strip().startswith("image/"))

    @staticmethod
    def _create_thumbnail_bytes(content: bytes, size: tuple[int, int]) -> bytes:
        with Image.open(BytesIO(content)) as image:
            image.thumbnail(size)
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")

            output = BytesIO()
            image.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()

    @staticmethod
    def ensure_configured() -> None:
        if not settings.asset_bucket_name:
            raise AssetStorageConfigError("ASSET_BUCKET_NAME is required.")

    @staticmethod
    def _upload_bytes(
        key: str,
        content: bytes,
        mime_type: str | None,
    ) -> None:
        client = boto3.client(
            "s3",
            endpoint_url=settings.asset_bucket_endpoint_url or None,
            region_name=settings.asset_bucket_region,
        )
        extra_args = {"ContentType": mime_type} if mime_type else {}
        client.put_object(
            Bucket=settings.asset_bucket_name,
            Key=key,
            Body=content,
            **extra_args,
        )

