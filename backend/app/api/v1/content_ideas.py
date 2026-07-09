from fastapi import APIRouter, Body, Depends, HTTPException, status
from kombu.exceptions import KombuError, OperationalError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.schemas import GenerationAcceptedRead, GenerationRequest
from app.services.higgsfield import GenerationJobNotFoundError, GenerationJobService

router = APIRouter(prefix="/content-ideas", tags=["content-ideas"])


@router.post(
    "/{content_idea_id}/generate",
    response_model=GenerationAcceptedRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_content_idea(
    content_idea_id: int,
    payload: GenerationRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> GenerationAcceptedRead:
    service = GenerationJobService(session)
    request = payload or GenerationRequest()

    try:
        job = await service.create_generation_job(content_idea_id, request)
    except GenerationJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    try:
        service.enqueue(job.id)
    except (KombuError, OperationalError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Generation job was created, but the worker queue is unavailable.",
        ) from exc

    return GenerationAcceptedRead(job_id=job.id, status="accepted")

