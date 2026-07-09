from datetime import UTC, datetime

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models import PlatformPost, Product
from app.services.analytics import AnalyticsService
from app.services.publishers.idempotency import (
    PublishIdempotencyService,
    PublishReservation,
)

SUPPORTED_PINTEREST_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/pjpeg",
    "image/tiff",
}
MAX_PINTEREST_TITLE_LENGTH = 100
MAX_PINTEREST_DESCRIPTION_LENGTH = 800


class PinterestPublisherConfigError(RuntimeError):
    pass


class PinterestPublishError(RuntimeError):
    pass


class PinterestPublisher:
    def __init__(
        self,
        session: AsyncSession,
        client: httpx.AsyncClient | None = None,
        access_token: str | None = None,
        api_base_url: str | None = None,
        board_id: str | None = None,
        board_name: str | None = None,
        public_pin_base_url: str | None = None,
        store_base_url: str | None = None,
    ) -> None:
        self.session = session
        self.client = client or httpx.AsyncClient(timeout=60)
        self.access_token = (
            access_token
            if access_token is not None
            else settings.pinterest_access_token
        )
        self.api_base_url = (api_base_url or settings.pinterest_api_base_url).rstrip("/")
        self.board_id = board_id if board_id is not None else settings.pinterest_board_id
        self.board_name = (
            board_name if board_name is not None else settings.pinterest_board_name
        )
        self.public_pin_base_url = (
            public_pin_base_url or settings.pinterest_public_pin_base_url
        ).rstrip("/")
        self.store_base_url = (
            store_base_url
            if store_base_url is not None
            else settings.pellevista_store_base_url
        )

    async def publish_post(self, post_id: int) -> PlatformPost:
        post = await self.session.get(PlatformPost, post_id)
        if post is None:
            raise PinterestPublishError("Platform post not found.")

        return await self.publish_loaded_post(post)

    async def publish_loaded_post(self, post: PlatformPost) -> PlatformPost:
        if self._is_already_published(post):
            return post

        idempotency = PublishIdempotencyService(self.session)
        reservation: PublishReservation | None = None
        try:
            self._validate_post(post)
            reservation = await idempotency.reserve(post)
            if not reservation.should_publish:
                return await idempotency.apply_existing_result(post, reservation)

            product = await self._load_product(post)
            image_url = post.draft_media_url or ""
            await self.validate_image(image_url)
            board_id = await self.select_board()
            title = self.create_pin_title(post=post, product=product)
            description = self.create_pin_description(post=post, product=product)
            destination_url = self.destination_product_url(product)
            result = await self.publish_pin(
                board_id=board_id,
                title=title,
                description=description,
                image_url=image_url,
                destination_url=destination_url,
            )
        except Exception as exc:
            if reservation is not None and reservation.should_publish:
                idempotency.mark_failed(reservation.attempt, str(exc))
            await self._mark_failed(post, str(exc))
            raise

        if reservation is None:
            raise PinterestPublishError("Pinterest publish reservation was not created.")

        published_at = datetime.now(UTC)
        post.external_post_id = result["id"]
        post.external_post_url = result.get(
            "url",
            f"{self.public_pin_base_url}/{result['id']}/",
        )
        post.publish_error = None
        post.status = "published"
        post.published_at = published_at
        post.updated_at = published_at
        idempotency.mark_published(
            attempt=reservation.attempt,
            external_post_id=post.external_post_id,
            external_post_url=post.external_post_url,
            published_at=published_at,
        )
        await AnalyticsService(self.session).record_published_post(post)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def select_board(self) -> str:
        self._ensure_configured()
        if self.board_id:
            return self.board_id

        response = await self.client.get(
            f"{self.api_base_url}/boards",
            headers=self._headers(),
        )
        response.raise_for_status()
        payload = response.json()
        boards = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(boards, list) or not boards:
            raise PinterestPublisherConfigError("No Pinterest board is available.")

        if self.board_name:
            for board in boards:
                if (
                    isinstance(board, dict)
                    and board.get("name") == self.board_name
                    and isinstance(board.get("id"), str)
                ):
                    return board["id"]

            raise PinterestPublisherConfigError(
                f"Pinterest board named {self.board_name!r} was not found.",
            )

        first_board = boards[0]
        if not isinstance(first_board, dict) or not isinstance(first_board.get("id"), str):
            raise PinterestPublisherConfigError("Pinterest board response is invalid.")

        return first_board["id"]

    async def validate_image(self, image_url: str) -> None:
        if not image_url:
            raise PinterestPublishError("Pinterest image URL is required.")

        response = await self.client.head(image_url)
        response.raise_for_status()
        media_type = response.headers.get("content-type", "").split(";")[0].lower()
        if media_type not in SUPPORTED_PINTEREST_IMAGE_TYPES:
            raise PinterestPublishError(
                "Only image media is supported for Pinterest publishing in v1.",
            )

    async def publish_pin(
        self,
        board_id: str,
        title: str,
        description: str,
        image_url: str,
        destination_url: str,
    ) -> dict[str, str]:
        self._ensure_configured()
        payload = {
            "board_id": board_id,
            "title": title,
            "description": description,
            "link": destination_url,
            "alt_text": title,
            "media_source": {
                "source_type": "image_url",
                "url": image_url,
            },
        }
        response = await self.client.post(
            f"{self.api_base_url}/pins",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        pin_id = data.get("id") if isinstance(data, dict) else None
        if not isinstance(pin_id, str) or not pin_id:
            raise PinterestPublishError("Pinterest create Pin response did not include a Pin id.")

        pin_url = data.get("url") if isinstance(data, dict) else None
        result = {"id": pin_id}
        if isinstance(pin_url, str) and pin_url:
            result["url"] = pin_url

        return result

    def create_pin_title(self, post: PlatformPost, product: Product) -> str:
        title = self._extract_pinterest_field(post.draft_caption, "Title")
        if not title:
            title = f"Handcrafted Men's {product.title}"

        return self._truncate(title, MAX_PINTEREST_TITLE_LENGTH)

    def create_pin_description(self, post: PlatformPost, product: Product) -> str:
        description = self._extract_pinterest_field(post.draft_caption, "Description")
        if not description:
            description = (
                f"Premium handcrafted men's leather shoes from PelleVista. "
                f"Explore {product.title} for formal outfits, weddings, office wear, "
                "and luxury style."
            )

        return self._truncate(description, MAX_PINTEREST_DESCRIPTION_LENGTH)

    def destination_product_url(self, product: Product) -> str:
        base_url = self.store_base_url.strip().rstrip("/")
        if not base_url:
            shopify_domain = settings.shopify_shop_domain.strip()
            if shopify_domain:
                base_url = shopify_domain.rstrip("/")
                if not base_url.startswith(("http://", "https://")):
                    base_url = f"https://{base_url}"

        if not base_url:
            raise PinterestPublisherConfigError("PELLEVISTA_STORE_BASE_URL is required.")

        return f"{base_url}/products/{product.handle}"

    async def _load_product(self, post: PlatformPost) -> Product:
        if post.product_id is None:
            raise PinterestPublishError("Pinterest post must reference a product.")

        product = await self.session.get(Product, post.product_id)
        if product is None:
            raise PinterestPublishError("Pinterest post product was not found.")

        return product

    def _validate_post(self, post: PlatformPost) -> None:
        if post.platform.lower() != "pinterest":
            raise PinterestPublishError("PinterestPublisher can only publish Pinterest posts.")
        if not post.draft_caption.strip():
            raise PinterestPublishError("Pinterest caption cannot be empty.")
        if post.status not in {"approved", "scheduled", "publishing", "failed"}:
            raise PinterestPublishError(
                "Pinterest post must be approved, scheduled, publishing, or failed.",
            )

    @staticmethod
    def _is_already_published(post: PlatformPost) -> bool:
        return post.status == "published" or bool(post.external_post_id)

    def _ensure_configured(self) -> None:
        if not self.access_token:
            raise PinterestPublisherConfigError("PINTEREST_ACCESS_TOKEN is required.")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_pinterest_field(caption: str, field_name: str) -> str | None:
        lines = caption.strip().splitlines()
        marker = f"{field_name}:"
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith(marker):
                continue

            value = stripped.removeprefix(marker).strip()
            if value:
                return value

            collected: list[str] = []
            for next_line in lines[index + 1 :]:
                next_value = next_line.strip()
                if not next_value:
                    continue
                if next_value.endswith(":"):
                    break
                collected.append(next_value)

            return " ".join(collected) or None

        return None

    @staticmethod
    def _truncate(value: str, max_length: int) -> str:
        clean_value = " ".join(value.split())
        if len(clean_value) <= max_length:
            return clean_value

        return clean_value[: max_length - 1].rstrip() + "..."

    async def _mark_failed(self, post: PlatformPost, message: str) -> None:
        post.status = "failed"
        post.publish_error = message
        post.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(post)
