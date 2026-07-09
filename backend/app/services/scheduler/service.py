from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import ContentIdea, GeneratedAsset, GenerationJob, PlatformPost, Product
from app.schemas import GenerationRequest
from app.services.content_strategy import ContentStrategyService
from app.services.publishers import (
    META_DEFERRED_MESSAGE,
    META_DEFERRED_PLATFORMS,
    PinterestPublisher,
    XPublisher,
)
from app.services.prompt_builder import PLATFORM_FORMATS
from app.services.scheduler.schedule import slot_for_idea_platform
from app.services.shopify import ProductSyncService
from app.services.shopify.sync_status import mark_completed, mark_failed, mark_running

PLATFORM_NAME_MAP = {
    "X": "x",
    "Facebook": "facebook",
    "Instagram": "instagram",
    "Pinterest": "pinterest",
}
POST_PREPARE_STATUSES = {"draft", "generated", "needs_review", "approved"}
ASSET_PREPARE_STATUSES = {"approved", "generated", "needs_review"}


class SchedulerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sync_shopify_products(self) -> tuple[int, int]:
        mark_running()
        try:
            products_synced, images_synced = await ProductSyncService(self.session).sync()
        except Exception as exc:
            mark_failed(str(exc))
            raise

        mark_completed(products_synced=products_synced, images_synced=images_synced)
        return products_synced, images_synced

    async def create_daily_content_plan(
        self,
        plan_date: date,
        number_of_ideas: int = 2,
    ) -> tuple[int, int]:
        plan = await ContentStrategyService(self.session).create_daily_plan(
            plan_date=plan_date,
            number_of_ideas=number_of_ideas,
        )
        created_ideas = 0
        created_posts = 0
        start_at, end_at = self._date_window(plan_date)

        for content_idea in plan.content_ideas:
            product = await self._find_product_by_title(content_idea.product_title)
            if product is None or product.id is None:
                continue

            existing = await self._find_existing_content_idea(
                product_id=product.id,
                title=content_idea.pillar,
                start_at=start_at,
                end_at=end_at,
            )
            if existing is not None:
                continue

            idea = ContentIdea(
                brand_id=product.brand_id,
                product_id=product.id,
                title=content_idea.pillar,
                angle=content_idea.angle,
                status="draft",
            )
            self.session.add(idea)
            await self.session.flush()
            if idea.id is None:
                continue

            for draft in content_idea.platform_post_drafts:
                self.session.add(
                    PlatformPost(
                        content_idea_id=idea.id,
                        product_id=product.id,
                        platform=self._platform_key(draft.platform),
                        status="draft",
                        draft_caption=draft.draft_caption,
                    ),
                )
                created_posts += 1

            created_ideas += 1

        await self.session.commit()
        return created_ideas, created_posts

    async def enqueue_daily_asset_generation(self, plan_date: date) -> list[UUID]:
        ideas = await self._content_ideas_for_date(plan_date)
        created_jobs: list[GenerationJob] = []

        for idea in ideas:
            if idea.id is None:
                continue
            posts = await self._platform_posts_for_idea(idea.id)
            for post in posts:
                platform = self._platform_key(post.platform)
                if await self._has_generation_job(idea.id, platform):
                    continue

                platform_format = PLATFORM_FORMATS[platform]
                job = GenerationJob(
                    content_idea_id=idea.id,
                    platform=platform,
                    status="accepted",
                    aspect_ratio=platform_format["aspect_ratio"],
                    asset_type=platform_format["asset_type"],
                    creative_style=GenerationRequest().creative_style,
                )
                self.session.add(job)
                created_jobs.append(job)

        await self.session.commit()
        for job in created_jobs:
            self.enqueue_generation(job.id)

        return [job.id for job in created_jobs]

    def enqueue_generation(self, job_id: UUID) -> None:
        from app.workers.tasks import generate_content_asset

        generate_content_asset.delay(str(job_id))

    async def prepare_daily_posts(self, plan_date: date) -> int:
        ideas = await self._content_ideas_for_date(plan_date)
        prepared_count = 0

        for idea_index, idea in enumerate(ideas):
            if idea.id is None:
                continue

            posts = await self._platform_posts_for_idea(idea.id)
            for post in posts:
                if post.status not in POST_PREPARE_STATUSES:
                    continue

                asset = await self._asset_for_platform(
                    content_idea_id=idea.id,
                    platform=self._platform_key(post.platform),
                )
                if asset is not None:
                    post.draft_media_url = asset.storage_url

                post.scheduled_for = slot_for_idea_platform(
                    plan_date=plan_date,
                    idea_index=idea_index,
                    platform=post.platform,
                ).scheduled_for
                if post.status in {"draft", "generated"}:
                    post.status = "needs_review"
                post.updated_at = datetime.now(UTC)
                prepared_count += 1

        await self.session.commit()
        return prepared_count

    async def publish_due_scheduled_posts(
        self,
        now: datetime | None = None,
    ) -> int:
        due_at = self._normalize_datetime(now or datetime.now(UTC))
        result = await self.session.exec(
            select(PlatformPost)
            .where(PlatformPost.status == "scheduled")
            .where(PlatformPost.scheduled_for <= due_at)
            .order_by(col(PlatformPost.scheduled_for), col(PlatformPost.id)),
        )
        posts = result.all()

        for post in posts:
            platform = self._platform_key(post.platform)
            if platform == "x":
                try:
                    await XPublisher(self.session).publish_loaded_post(post)
                except Exception:
                    continue
            elif platform == "pinterest":
                try:
                    await PinterestPublisher(self.session).publish_loaded_post(post)
                except Exception:
                    continue
            elif platform in META_DEFERRED_PLATFORMS:
                post.publish_error = META_DEFERRED_MESSAGE
                post.updated_at = datetime.now(UTC)
            else:
                post.status = "publishing"
                post.updated_at = datetime.now(UTC)

        await self.session.commit()
        return len(posts)

    async def _find_product_by_title(self, title: str) -> Product | None:
        result = await self.session.exec(
            select(Product)
            .where(Product.title == title)
            .order_by(col(Product.priority_score).desc())
            .limit(1),
        )
        return result.one_or_none()

    async def _find_existing_content_idea(
        self,
        product_id: int,
        title: str,
        start_at: datetime,
        end_at: datetime,
    ) -> ContentIdea | None:
        result = await self.session.exec(
            select(ContentIdea)
            .where(ContentIdea.product_id == product_id)
            .where(ContentIdea.title == title)
            .where(ContentIdea.created_at >= start_at)
            .where(ContentIdea.created_at < end_at)
            .limit(1),
        )
        return result.one_or_none()

    async def _content_ideas_for_date(self, plan_date: date) -> list[ContentIdea]:
        start_at, end_at = self._date_window(plan_date)
        result = await self.session.exec(
            select(ContentIdea)
            .where(ContentIdea.created_at >= start_at)
            .where(ContentIdea.created_at < end_at)
            .order_by(col(ContentIdea.created_at), col(ContentIdea.id)),
        )
        return list(result.all())

    async def _platform_posts_for_idea(self, content_idea_id: int) -> list[PlatformPost]:
        result = await self.session.exec(
            select(PlatformPost)
            .where(PlatformPost.content_idea_id == content_idea_id)
            .order_by(col(PlatformPost.id)),
        )
        return list(result.all())

    async def _has_generation_job(self, content_idea_id: int, platform: str) -> bool:
        result = await self.session.exec(
            select(GenerationJob)
            .where(GenerationJob.content_idea_id == content_idea_id)
            .where(GenerationJob.platform == platform)
            .limit(1),
        )
        return result.one_or_none() is not None

    async def _asset_for_platform(
        self,
        content_idea_id: int,
        platform: str,
    ) -> GeneratedAsset | None:
        result = await self.session.exec(
            select(GeneratedAsset)
            .where(GeneratedAsset.content_idea_id == content_idea_id)
            .where(GeneratedAsset.platform == platform)
            .where(col(GeneratedAsset.status).in_(ASSET_PREPARE_STATUSES))
            .order_by(col(GeneratedAsset.created_at).desc())
            .limit(1),
        )
        return result.one_or_none()

    @staticmethod
    def _platform_key(platform: str) -> str:
        return PLATFORM_NAME_MAP.get(platform, platform.lower())

    @staticmethod
    def _date_window(plan_date: date) -> tuple[datetime, datetime]:
        start_at = datetime.combine(plan_date, datetime.min.time(), tzinfo=UTC)
        return start_at, start_at + timedelta(days=1)

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)


def today_utc() -> date:
    return datetime.now(UTC).date()
