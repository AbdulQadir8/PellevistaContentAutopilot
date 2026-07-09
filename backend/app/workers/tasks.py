import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import engine
from app.models import (
    Brand,
    ContentIdea,
    GeneratedAsset,
    GenerationJob,
    Product,
    ProductImage,
)
from app.schemas import (
    PlatformName,
    PromptProductImageInput,
    PromptProductInput,
)
from app.services.analytics import AnalyticsService
from app.services.assets import AssetStorageService
from app.services.higgsfield import HiggsfieldGenerator, normalize_content_pillar
from app.services.prompt_builder import PromptBuilderService
from app.services.scheduler import SchedulerService, today_utc
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.generate_content_asset")
def generate_content_asset(job_id: str) -> None:
    asyncio.run(run_generate_content_asset(UUID(job_id)))


@celery_app.task(name="app.workers.tasks.sync_shopify_products")
def sync_shopify_products() -> dict[str, int]:
    return asyncio.run(run_sync_shopify_products())


@celery_app.task(name="app.workers.tasks.create_daily_content_plan")
def create_daily_content_plan() -> dict[str, int]:
    return asyncio.run(run_create_daily_content_plan())


@celery_app.task(name="app.workers.tasks.generate_daily_assets")
def generate_daily_assets() -> dict[str, int]:
    return asyncio.run(run_generate_daily_assets())


@celery_app.task(name="app.workers.tasks.prepare_daily_posts")
def prepare_daily_posts() -> dict[str, int]:
    return asyncio.run(run_prepare_daily_posts())


@celery_app.task(name="app.workers.tasks.publish_due_scheduled_posts")
def publish_due_scheduled_posts() -> dict[str, int]:
    return asyncio.run(run_publish_due_scheduled_posts())


@celery_app.task(name="app.workers.tasks.collect_due_analytics")
def collect_due_analytics() -> dict[str, int]:
    return asyncio.run(run_collect_due_analytics())


async def run_generate_content_asset(job_id: UUID) -> None:
    async with AsyncSession(engine) as session:
        job = await session.get(GenerationJob, job_id)
        if job is None:
            return

        try:
            job.status = "running"
            job.updated_at = datetime.now(UTC)
            await session.commit()

            content_idea = await _load_content_idea(session, job)
            product = await _load_product(session, content_idea)
            product_image = await _load_product_image(session, product)

            prompt_output = PromptBuilderService().build_from_parts(
                product=PromptProductInput(
                    title=product.title,
                    product_type=product.product_type,
                    tags=_parse_tags(product.tags),
                    price=product.price,
                ),
                product_image=PromptProductImageInput(
                    url=product_image.url,
                    alt_text=product_image.alt_text,
                ),
                content_pillar=normalize_content_pillar(content_idea.title),
                angle=content_idea.angle,
                platform=cast(PlatformName, job.platform),
                aspect_ratio=job.aspect_ratio,
                creative_style=job.creative_style,
            )

            job.prompt = prompt_output.higgsfield_prompt
            job.negative_prompt = prompt_output.negative_prompt
            job.reference_image_url = product_image.url

            generation_result = await HiggsfieldGenerator().generate(
                prompt=prompt_output.higgsfield_prompt,
                reference_image_url=product_image.url,
                aspect_ratio=job.aspect_ratio,
            )
            job.higgsfield_request_id = generation_result.request_id
            job.higgsfield_result_url = generation_result.result_url

            brand = await _load_brand(session, content_idea)
            if product.id is None:
                raise ValueError("Product must be persisted before asset storage.")

            asset_id = uuid4()
            stored_asset = await AssetStorageService().upload_generated_asset(
                source_url=generation_result.result_url,
                brand_slug=brand.slug,
                product_id=product.id,
                platform=job.platform,
                asset_date=job.created_at.date(),
                asset_id=asset_id,
                asset_type=job.asset_type,
            )
            session.add(
                GeneratedAsset(
                    id=asset_id,
                    generation_job_id=job.id,
                    content_idea_id=job.content_idea_id,
                    platform=job.platform,
                    asset_type=job.asset_type,
                    source_url=stored_asset.source_url,
                    storage_url=stored_asset.storage_url,
                    storage_key=stored_asset.storage_key,
                    thumbnail_url=stored_asset.thumbnail_url,
                    thumbnail_storage_key=stored_asset.thumbnail_storage_key,
                    mime_type=stored_asset.mime_type,
                    file_size_bytes=stored_asset.file_size_bytes,
                ),
            )

            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            await _mark_failed(session, job_id, str(exc))


async def run_sync_shopify_products() -> dict[str, int]:
    async with AsyncSession(engine) as session:
        products_synced, images_synced = await SchedulerService(
            session,
        ).sync_shopify_products()
        return {
            "products_synced": products_synced,
            "images_synced": images_synced,
        }


async def run_create_daily_content_plan() -> dict[str, int]:
    async with AsyncSession(engine) as session:
        ideas_created, posts_created = await SchedulerService(
            session,
        ).create_daily_content_plan(plan_date=today_utc())
        return {
            "ideas_created": ideas_created,
            "posts_created": posts_created,
        }


async def run_generate_daily_assets() -> dict[str, int]:
    async with AsyncSession(engine) as session:
        job_ids = await SchedulerService(
            session,
        ).enqueue_daily_asset_generation(plan_date=today_utc())
        return {"jobs_enqueued": len(job_ids)}


async def run_prepare_daily_posts() -> dict[str, int]:
    async with AsyncSession(engine) as session:
        posts_prepared = await SchedulerService(
            session,
        ).prepare_daily_posts(plan_date=today_utc())
        return {"posts_prepared": posts_prepared}


async def run_publish_due_scheduled_posts() -> dict[str, int]:
    async with AsyncSession(engine) as session:
        posts_started = await SchedulerService(session).publish_due_scheduled_posts()
        return {"posts_started": posts_started}


async def run_collect_due_analytics() -> dict[str, int]:
    async with AsyncSession(engine) as session:
        snapshots_collected = await AnalyticsService(session).collect_due_snapshots()
        return {"snapshots_collected": snapshots_collected}


async def _load_content_idea(
    session: AsyncSession,
    job: GenerationJob,
) -> ContentIdea:
    content_idea = await session.get(ContentIdea, job.content_idea_id)
    if content_idea is None:
        raise ValueError("Content idea not found.")

    return content_idea


async def _load_product(session: AsyncSession, content_idea: ContentIdea) -> Product:
    if content_idea.product_id is None:
        raise ValueError("Content idea must reference a product.")

    product = await session.get(Product, content_idea.product_id)
    if product is None:
        raise ValueError("Product not found.")

    return product


async def _load_brand(session: AsyncSession, content_idea: ContentIdea) -> Brand:
    brand = await session.get(Brand, content_idea.brand_id)
    if brand is None:
        raise ValueError("Brand not found.")

    return brand


async def _load_product_image(
    session: AsyncSession,
    product: Product,
) -> ProductImage:
    result = await session.exec(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(ProductImage.position)
        .limit(1),
    )
    image = result.one_or_none()
    if image is None:
        raise ValueError("Product must have a usable image.")

    return image


async def _mark_failed(session: AsyncSession, job_id: UUID, message: str) -> None:
    job = await session.get(GenerationJob, job_id)
    if job is None:
        return

    job.status = "failed"
    job.error_message = message
    job.completed_at = datetime.now(UTC)
    job.updated_at = datetime.now(UTC)
    await session.commit()


def _parse_tags(tags: str | None) -> list[str]:
    if not tags:
        return []

    return [tag.strip() for tag in tags.split(",") if tag.strip()]
