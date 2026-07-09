import base64
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models import PlatformPost
from app.services.analytics import AnalyticsService
from app.services.publishers.idempotency import (
    PublishIdempotencyService,
    PublishReservation,
)

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/pjpeg",
    "image/tiff",
}
MAX_X_CAPTION_LENGTH = 280


class XPublisherConfigError(RuntimeError):
    pass


class XPublishError(RuntimeError):
    pass


class XPublisher:
    def __init__(
        self,
        session: AsyncSession,
        client: httpx.AsyncClient | None = None,
        access_token: str | None = None,
        api_base_url: str | None = None,
        public_post_base_url: str | None = None,
    ) -> None:
        self.session = session
        self.client = client or httpx.AsyncClient(timeout=60)
        self.access_token = access_token if access_token is not None else settings.x_user_access_token
        self.api_base_url = (api_base_url or settings.x_api_base_url).rstrip("/")
        self.public_post_base_url = (
            public_post_base_url or settings.x_public_post_base_url
        ).rstrip("/")

    async def publish_post(self, post_id: int) -> PlatformPost:
        post = await self.session.get(PlatformPost, post_id)
        if post is None:
            raise XPublishError("Platform post not found.")

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

            media_id = None
            if post.draft_media_url:
                media_id = await self.upload_media(post.draft_media_url)

            result = await self.create_post(
                caption=post.draft_caption.strip(),
                media_id=media_id,
            )
        except Exception as exc:
            if reservation is not None and reservation.should_publish:
                idempotency.mark_failed(reservation.attempt, str(exc))
            await self._mark_failed(post, str(exc))
            raise

        if reservation is None:
            raise XPublishError("X publish reservation was not created.")

        published_at = datetime.now(UTC)
        post.external_post_id = result["id"]
        post.external_post_url = f"{self.public_post_base_url}/{result['id']}"
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

    async def upload_media(self, media_url: str) -> str:
        self._ensure_configured()
        media_response = await self.client.get(media_url)
        media_response.raise_for_status()
        media_type = self._media_type(media_response)
        if media_type not in SUPPORTED_IMAGE_TYPES:
            raise XPublishError(
                "Only image media is supported for X publishing in v1.",
            )

        payload = {
            "media": base64.b64encode(media_response.content).decode("ascii"),
            "media_category": "tweet_image",
            "media_type": media_type,
            "shared": False,
        }
        response = await self.client.post(
            f"{self.api_base_url}/2/media/upload",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        data = self._data(response)
        media_id = data.get("id")
        if not isinstance(media_id, str) or not media_id:
            raise XPublishError("X media upload did not return a media id.")

        return media_id

    async def create_post(self, caption: str, media_id: str | None = None) -> dict[str, str]:
        self._ensure_configured()
        payload: dict[str, Any] = {"text": caption}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}

        response = await self.client.post(
            f"{self.api_base_url}/2/tweets",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        data = self._data(response)
        post_id = data.get("id")
        if not isinstance(post_id, str) or not post_id:
            raise XPublishError("X create post response did not include a post id.")

        return {"id": post_id}

    def _validate_post(self, post: PlatformPost) -> None:
        if post.platform.lower() != "x":
            raise XPublishError("XPublisher can only publish X posts.")

        caption = post.draft_caption.strip()
        if not caption:
            raise XPublishError("X caption cannot be empty.")
        if len(caption) > MAX_X_CAPTION_LENGTH:
            raise XPublishError("X caption must be 280 characters or fewer.")
        if post.status not in {"approved", "scheduled", "publishing", "failed"}:
            raise XPublishError(
                "X post must be approved, scheduled, publishing, or failed.",
            )

    @staticmethod
    def _is_already_published(post: PlatformPost) -> bool:
        return post.status == "published" or bool(post.external_post_id)

    def _ensure_configured(self) -> None:
        if not self.access_token:
            raise XPublisherConfigError("X_USER_ACCESS_TOKEN is required.")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _media_type(response: httpx.Response) -> str:
        return response.headers.get("content-type", "").split(";")[0].lower()

    @staticmethod
    def _data(response: httpx.Response) -> dict[str, Any]:
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise XPublishError("X response did not include a data object.")

        return data

    async def _mark_failed(self, post: PlatformPost, message: str) -> None:
        post.status = "failed"
        post.publish_error = message
        post.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(post)
