from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from kombu.exceptions import KombuError, OperationalError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.schemas import (
    AssetReviewActionRequest,
    GeneratedAssetRead,
    GenerationAcceptedRead,
)
from app.services.review import (
    ManualReviewService,
    ReviewWorkflowInvalidTransitionError,
    ReviewWorkflowNotFoundError,
)

router = APIRouter(prefix="/assets", tags=["manual-review"])


@router.post("/{asset_id}/approve", response_model=GeneratedAssetRead)
async def approve_asset(
    asset_id: UUID,
    payload: AssetReviewActionRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> GeneratedAssetRead:
    service = ManualReviewService(session)
    try:
        asset = await service.approve_asset(asset_id, payload.note if payload else None)
    except ReviewWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return GeneratedAssetRead.model_validate(asset)


@router.post("/{asset_id}/reject", response_model=GeneratedAssetRead)
async def reject_asset(
    asset_id: UUID,
    payload: AssetReviewActionRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> GeneratedAssetRead:
    service = ManualReviewService(session)
    try:
        asset = await service.reject_asset(asset_id, payload.note if payload else None)
    except ReviewWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return GeneratedAssetRead.model_validate(asset)


@router.post(
    "/{asset_id}/regenerate",
    response_model=GenerationAcceptedRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_asset(
    asset_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> GenerationAcceptedRead:
    service = ManualReviewService(session)
    try:
        job = await service.regenerate_asset(asset_id)
    except ReviewWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewWorkflowInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    try:
        service.enqueue_generation(job.id)
    except (KombuError, OperationalError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Generation job was created, but the worker queue is unavailable.",
        ) from exc

    return GenerationAcceptedRead(job_id=job.id, status="accepted")
