from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import PlatformPost, PublishAttempt

PUBLISHING_STATUSES = {"publishing", "reserved"}


@dataclass(frozen=True)
class PublishReservation:
    attempt: PublishAttempt
    should_publish: bool
    reason: str


class PublishIdempotencyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def reserve(self, post: PlatformPost) -> PublishReservation:
        scheduled_at = self.scheduled_at_for(post)
        post.scheduled_for = scheduled_at
        key = self.idempotency_key(
            platform_post_id=self._post_id(post),
            platform=post.platform,
            scheduled_at=scheduled_at,
        )
        existing = await self.session.get(PublishAttempt, key)
        if existing is not None:
            return await self._reserve_existing(existing, post)

        now = datetime.now(UTC)
        attempt = PublishAttempt(
            idempotency_key=key,
            platform_post_id=self._post_id(post),
            platform=post.platform.lower(),
            scheduled_at=scheduled_at,
            status="publishing",
            attempt_count=1,
            created_at=now,
            updated_at=now,
        )
        post.status = "publishing"
        post.publish_error = None
        post.updated_at = now
        self.session.add(attempt)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.session.get(PublishAttempt, key)
            if existing is None:
                raise
            return await self._reserve_existing(existing, post)

        await self.session.refresh(attempt)
        return PublishReservation(
            attempt=attempt,
            should_publish=True,
            reason="reserved",
        )

    async def apply_existing_result(
        self,
        post: PlatformPost,
        reservation: PublishReservation,
    ) -> PlatformPost:
        attempt = reservation.attempt
        if reservation.reason != "already_published":
            return post

        now = datetime.now(UTC)
        post.external_post_id = post.external_post_id or attempt.external_post_id
        post.external_post_url = post.external_post_url or attempt.external_post_url
        post.published_at = post.published_at or attempt.published_at
        post.publish_error = None
        post.status = "published"
        post.updated_at = now
        await self.session.commit()
        await self.session.refresh(post)
        return post

    def mark_published(
        self,
        attempt: PublishAttempt,
        external_post_id: str,
        external_post_url: str,
        published_at: datetime,
    ) -> None:
        attempt.status = "published"
        attempt.external_post_id = external_post_id
        attempt.external_post_url = external_post_url
        attempt.error_message = None
        attempt.published_at = published_at
        attempt.updated_at = datetime.now(UTC)

    def mark_failed(self, attempt: PublishAttempt, message: str) -> None:
        attempt.status = "failed"
        attempt.error_message = message
        attempt.updated_at = datetime.now(UTC)

    async def _reserve_existing(
        self,
        attempt: PublishAttempt,
        post: PlatformPost,
    ) -> PublishReservation:
        if attempt.status == "published":
            return PublishReservation(
                attempt=attempt,
                should_publish=False,
                reason="already_published",
            )
        if attempt.status in PUBLISHING_STATUSES:
            return PublishReservation(
                attempt=attempt,
                should_publish=False,
                reason="already_in_progress",
            )

        now = datetime.now(UTC)
        attempt.status = "publishing"
        attempt.attempt_count += 1
        attempt.error_message = None
        attempt.updated_at = now
        post.status = "publishing"
        post.publish_error = None
        post.updated_at = now
        await self.session.commit()
        await self.session.refresh(attempt)
        return PublishReservation(
            attempt=attempt,
            should_publish=True,
            reason="retry",
        )

    @staticmethod
    def idempotency_key(
        platform_post_id: int,
        platform: str,
        scheduled_at: datetime,
    ) -> str:
        return (
            f"{platform_post_id}:"
            f"{platform.lower()}:"
            f"{PublishIdempotencyService._normalize_datetime(scheduled_at).isoformat()}"
        )

    @staticmethod
    def scheduled_at_for(post: PlatformPost) -> datetime:
        return PublishIdempotencyService._normalize_datetime(
            post.scheduled_for or datetime.now(UTC),
        )

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    @staticmethod
    def _post_id(post: PlatformPost) -> int:
        if post.id is None:
            raise ValueError("Platform post must be persisted before publishing.")

        return post.id
