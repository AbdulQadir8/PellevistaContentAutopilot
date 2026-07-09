from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import GeneratedAsset, GenerationJob, PlatformPost
from app.schemas import PlatformPostScheduleRequest, PlatformPostUpdate
from app.services.prompt_builder import PLATFORM_FORMATS

EDIT_LOCKED_POST_STATUSES = {"publishing", "published", "cancelled"}
POST_APPROVAL_ALLOWED_STATUSES = {"draft", "generated", "needs_review", "approved"}
POST_SCHEDULE_ALLOWED_STATUSES = {"approved", "scheduled", "failed"}
POST_PUBLISH_NOW_ALLOWED_STATUSES = {"approved", "scheduled", "failed"}


class ReviewWorkflowError(RuntimeError):
    pass


class ReviewWorkflowNotFoundError(ReviewWorkflowError):
    pass


class ReviewWorkflowInvalidTransitionError(ReviewWorkflowError):
    pass


class ManualReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def approve_asset(self, asset_id: UUID, note: str | None = None) -> GeneratedAsset:
        asset = await self._get_asset(asset_id)
        asset.status = "approved"
        asset.review_note = note
        asset.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(asset)
        return asset

    async def reject_asset(self, asset_id: UUID, note: str | None = None) -> GeneratedAsset:
        asset = await self._get_asset(asset_id)
        asset.status = "failed"
        asset.review_note = note
        asset.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(asset)
        return asset

    async def regenerate_asset(self, asset_id: UUID) -> GenerationJob:
        asset = await self._get_asset(asset_id)
        original_job = await self.session.get(GenerationJob, asset.generation_job_id)
        platform = asset.platform.lower()
        if platform not in PLATFORM_FORMATS:
            raise ReviewWorkflowInvalidTransitionError(
                f"Unsupported generation platform: {asset.platform}.",
            )
        platform_format = PLATFORM_FORMATS[platform]

        job = GenerationJob(
            content_idea_id=asset.content_idea_id,
            platform=platform,
            status="accepted",
            aspect_ratio=(
                original_job.aspect_ratio
                if original_job
                else platform_format["aspect_ratio"]
            ),
            asset_type=(
                original_job.asset_type
                if original_job
                else platform_format["asset_type"]
            ),
            creative_style=(
                original_job.creative_style
                if original_job
                else "premium editorial menswear product advertisement"
            ),
        )
        asset.status = "cancelled"
        asset.review_note = "Regeneration requested."
        asset.updated_at = datetime.now(UTC)
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    def enqueue_generation(self, job_id: UUID) -> None:
        from app.workers.tasks import generate_content_asset

        generate_content_asset.delay(str(job_id))

    async def update_platform_post(
        self,
        post_id: int,
        payload: PlatformPostUpdate,
    ) -> PlatformPost:
        post = await self._get_post(post_id)
        if post.status in EDIT_LOCKED_POST_STATUSES:
            raise ReviewWorkflowInvalidTransitionError(
                f"Cannot edit a {post.status} post.",
            )

        data = payload.model_dump(exclude_unset=True)
        if "draft_caption" in data and data["draft_caption"] is not None:
            caption = data["draft_caption"].strip()
            if not caption:
                raise ReviewWorkflowInvalidTransitionError("Caption cannot be empty.")
            post.draft_caption = caption
            if post.status == "approved":
                post.status = "needs_review"

        if "draft_media_url" in data:
            post.draft_media_url = data["draft_media_url"]
            if post.status == "approved":
                post.status = "needs_review"

        if "scheduled_for" in data:
            post.scheduled_for = self._normalize_datetime(data["scheduled_for"])

        if "status" in data and data["status"] is not None:
            if data["status"] in {"publishing", "published"}:
                raise ReviewWorkflowInvalidTransitionError(
                    "Use the dedicated publish workflow for publishing statuses.",
                )
            post.status = data["status"]

        post.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def approve_platform_post(self, post_id: int) -> PlatformPost:
        post = await self._get_post(post_id)
        if post.status not in POST_APPROVAL_ALLOWED_STATUSES:
            raise ReviewWorkflowInvalidTransitionError(
                f"Cannot approve a {post.status} post.",
            )
        self._ensure_caption(post)
        post.status = "approved"
        post.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def schedule_platform_post(
        self,
        post_id: int,
        payload: PlatformPostScheduleRequest,
    ) -> PlatformPost:
        post = await self._get_post(post_id)
        if post.status not in POST_SCHEDULE_ALLOWED_STATUSES:
            raise ReviewWorkflowInvalidTransitionError(
                "Approve the post before scheduling it.",
            )
        self._ensure_caption(post)
        scheduled_for = self._normalize_datetime(payload.scheduled_for)
        if scheduled_for <= datetime.now(UTC):
            raise ReviewWorkflowInvalidTransitionError(
                "scheduled_for must be in the future.",
            )

        post.scheduled_for = scheduled_for
        post.status = "scheduled"
        post.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def publish_platform_post_now(self, post_id: int) -> PlatformPost:
        post = await self._get_post(post_id)
        if post.status not in POST_PUBLISH_NOW_ALLOWED_STATUSES:
            raise ReviewWorkflowInvalidTransitionError(
                "Approve or schedule the post before publishing.",
            )
        self._ensure_caption(post)
        now = datetime.now(UTC)
        was_failed = post.status == "failed"
        post.status = "publishing"
        post.scheduled_for = post.scheduled_for if was_failed and post.scheduled_for else now
        post.updated_at = now
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def cancel_platform_post(self, post_id: int) -> PlatformPost:
        post = await self._get_post(post_id)
        if post.status in {"published", "publishing"}:
            raise ReviewWorkflowInvalidTransitionError(
                f"Cannot cancel a {post.status} post.",
            )
        post.status = "cancelled"
        post.updated_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def _get_asset(self, asset_id: UUID) -> GeneratedAsset:
        asset = await self.session.get(GeneratedAsset, asset_id)
        if asset is None:
            raise ReviewWorkflowNotFoundError("Generated asset not found.")

        return asset

    async def _get_post(self, post_id: int) -> PlatformPost:
        post = await self.session.get(PlatformPost, post_id)
        if post is None:
            raise ReviewWorkflowNotFoundError("Platform post not found.")

        return post

    @staticmethod
    def _ensure_caption(post: PlatformPost) -> None:
        if not post.draft_caption.strip():
            raise ReviewWorkflowInvalidTransitionError("Caption cannot be empty.")

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)


async def find_platform_post_for_asset(
    session: AsyncSession,
    asset: GeneratedAsset,
) -> PlatformPost | None:
    result = await session.exec(
        select(PlatformPost)
        .where(PlatformPost.content_idea_id == asset.content_idea_id)
        .where(PlatformPost.platform == asset.platform)
        .limit(1),
    )
    return result.one_or_none()
