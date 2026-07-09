from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.models import PlatformPost
from app.schemas import (
    PlatformPostRead,
    PlatformPostScheduleRequest,
    PlatformPostUpdate,
)
from app.services.review import (
    ManualReviewService,
    ReviewWorkflowInvalidTransitionError,
    ReviewWorkflowNotFoundError,
)
from app.services.publishers import (
    META_DEFERRED_MESSAGE,
    META_DEFERRED_PLATFORMS,
    PinterestPublisher,
    PinterestPublisherConfigError,
    PinterestPublishError,
    XPublisher,
    XPublisherConfigError,
    XPublishError,
)

router = APIRouter(prefix="/platform-posts", tags=["manual-review"])


@router.patch("/{post_id}", response_model=PlatformPostRead)
async def update_platform_post(
    post_id: int,
    payload: PlatformPostUpdate,
    session: AsyncSession = Depends(get_session),
) -> PlatformPostRead:
    service = ManualReviewService(session)
    try:
        post = await service.update_platform_post(post_id, payload)
    except ReviewWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewWorkflowInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return PlatformPostRead.model_validate(post)


@router.post("/{post_id}/approve", response_model=PlatformPostRead)
async def approve_platform_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
) -> PlatformPostRead:
    service = ManualReviewService(session)
    try:
        post = await service.approve_platform_post(post_id)
    except ReviewWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewWorkflowInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return PlatformPostRead.model_validate(post)


@router.post("/{post_id}/schedule", response_model=PlatformPostRead)
async def schedule_platform_post(
    post_id: int,
    payload: PlatformPostScheduleRequest,
    session: AsyncSession = Depends(get_session),
) -> PlatformPostRead:
    service = ManualReviewService(session)
    try:
        post = await service.schedule_platform_post(post_id, payload)
    except ReviewWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewWorkflowInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return PlatformPostRead.model_validate(post)


@router.post("/{post_id}/publish-now", response_model=PlatformPostRead)
async def publish_platform_post_now(
    post_id: int,
    session: AsyncSession = Depends(get_session),
) -> PlatformPostRead:
    service = ManualReviewService(session)
    try:
        existing_post = await session.get(PlatformPost, post_id)
        if existing_post is None:
            raise ReviewWorkflowNotFoundError("Platform post not found.")
        if existing_post.platform.lower() in META_DEFERRED_PLATFORMS:
            existing_post.publish_error = META_DEFERRED_MESSAGE
            existing_post.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(existing_post)
            raise ReviewWorkflowInvalidTransitionError(META_DEFERRED_MESSAGE)

        post = await service.publish_platform_post_now(post_id)
        if post.platform.lower() == "x":
            post = await XPublisher(session).publish_loaded_post(post)
        if post.platform.lower() == "pinterest":
            post = await PinterestPublisher(session).publish_loaded_post(post)
    except ReviewWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewWorkflowInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except XPublisherConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except XPublishError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except PinterestPublisherConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PinterestPublishError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return PlatformPostRead.model_validate(post)


@router.post("/{post_id}/cancel", response_model=PlatformPostRead)
async def cancel_platform_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
) -> PlatformPostRead:
    service = ManualReviewService(session)
    try:
        post = await service.cancel_platform_post(post_id)
    except ReviewWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewWorkflowInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return PlatformPostRead.model_validate(post)
