from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import ContentIdea, GenerationJob
from app.schemas import GenerationRequest
from app.services.content_strategy.templates import CONTENT_PILLARS
from app.services.prompt_builder import PLATFORM_FORMATS


class GenerationJobNotFoundError(RuntimeError):
    pass


class GenerationJobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_generation_job(
        self,
        content_idea_id: int,
        request: GenerationRequest,
    ) -> GenerationJob:
        content_idea = await self.session.get(ContentIdea, content_idea_id)
        if content_idea is None:
            raise GenerationJobNotFoundError("Content idea not found.")

        platform_format = PLATFORM_FORMATS[request.platform]
        job = GenerationJob(
            content_idea_id=content_idea_id,
            platform=request.platform,
            status="accepted",
            aspect_ratio=request.aspect_ratio or platform_format["aspect_ratio"],
            asset_type=platform_format["asset_type"],
            creative_style=request.creative_style,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    def enqueue(self, job_id: UUID) -> None:
        from app.workers.tasks import generate_content_asset

        generate_content_asset.delay(str(job_id))


def normalize_content_pillar(value: str) -> str:
    if value in CONTENT_PILLARS:
        return value

    return "Product beauty"
