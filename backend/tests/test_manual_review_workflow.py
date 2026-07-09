from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.main import app
from app.models import GeneratedAsset, GenerationJob, PlatformPost
from app.schemas import WorkflowStatus
from app.services.review import ManualReviewService


class FakeManualReviewSession:
    def __init__(
        self,
        assets: list[GeneratedAsset] | None = None,
        jobs: list[GenerationJob] | None = None,
        posts: list[PlatformPost] | None = None,
    ) -> None:
        self.assets = {asset.id: asset for asset in assets or []}
        self.jobs = {job.id: job for job in jobs or []}
        self.posts = {post.id: post for post in posts or [] if post.id is not None}
        self.added_jobs: list[GenerationJob] = []

    async def get(self, model: type[object], entity_id: object) -> object | None:
        if model is GeneratedAsset:
            return self.assets.get(entity_id)
        if model is GenerationJob:
            return self.jobs.get(entity_id)
        if model is PlatformPost:
            return self.posts.get(entity_id)

        return None

    def add(self, model: object) -> None:
        if isinstance(model, GenerationJob):
            self.jobs[model.id] = model
            self.added_jobs.append(model)

    async def commit(self) -> None:
        return None

    async def refresh(self, model: object) -> None:
        return None


def _asset(asset_id: UUID, job_id: UUID) -> GeneratedAsset:
    return GeneratedAsset(
        id=asset_id,
        generation_job_id=job_id,
        content_idea_id=1,
        platform="instagram",
        asset_type="video",
        source_url="https://higgsfield.example/generated.mp4",
        storage_url="https://cdn.pellevista.example/generated.mp4",
        status="generated",
    )


def _job(job_id: UUID) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        content_idea_id=1,
        platform="instagram",
        status="completed",
        aspect_ratio="9:16",
        asset_type="video",
        creative_style="premium studio video",
    )


def _post(post_id: int, status: str = "draft") -> PlatformPost:
    return PlatformPost(
        id=post_id,
        content_idea_id=1,
        product_id=1,
        platform="instagram",
        status=status,
        draft_caption="A sharp suit deserves shoes that match the effort.",
    )


def test_manual_review_statuses_match_production_workflow() -> None:
    statuses: set[WorkflowStatus] = {
        "draft",
        "generated",
        "needs_review",
        "approved",
        "scheduled",
        "publishing",
        "published",
        "failed",
        "cancelled",
    }

    assert statuses == {
        "draft",
        "generated",
        "needs_review",
        "approved",
        "scheduled",
        "publishing",
        "published",
        "failed",
        "cancelled",
    }


@pytest.mark.asyncio
async def test_asset_review_endpoints_approve_reject_and_regenerate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = uuid4()
    job_id = uuid4()
    fake_session = FakeManualReviewSession(
        assets=[_asset(asset_id, job_id)],
        jobs=[_job(job_id)],
    )
    enqueued_job_ids: list[UUID] = []

    async def override_get_session() -> FakeManualReviewSession:
        return fake_session

    def fake_enqueue(self: ManualReviewService, new_job_id: UUID) -> None:
        enqueued_job_ids.append(new_job_id)

    monkeypatch.setattr(ManualReviewService, "enqueue_generation", fake_enqueue)
    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            approve_response = await client.post(
                f"/api/v1/assets/{asset_id}/approve",
                json={"note": "Clean product identity."},
            )
            reject_response = await client.post(
                f"/api/v1/assets/{asset_id}/reject",
                json={"note": "Wrong shoe details."},
            )
            regenerate_response = await client.post(
                f"/api/v1/assets/{asset_id}/regenerate",
            )
    finally:
        app.dependency_overrides.clear()

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert approve_response.json()["review_note"] == "Clean product identity."
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "failed"
    assert reject_response.json()["review_note"] == "Wrong shoe details."
    assert regenerate_response.status_code == 202
    assert regenerate_response.json()["status"] == "accepted"
    assert fake_session.assets[asset_id].status == "cancelled"
    assert len(fake_session.added_jobs) == 1
    assert enqueued_job_ids == [fake_session.added_jobs[0].id]


@pytest.mark.asyncio
async def test_platform_post_review_endpoints_edit_approve_schedule_and_defer_meta_publish() -> None:
    fake_session = FakeManualReviewSession(posts=[_post(1)])

    async def override_get_session() -> FakeManualReviewSession:
        return fake_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            patch_response = await client.patch(
                "/api/v1/platform-posts/1",
                json={"draft_caption": "Edited PelleVista caption."},
            )
            approve_response = await client.post("/api/v1/platform-posts/1/approve")
            schedule_response = await client.post(
                "/api/v1/platform-posts/1/schedule",
                json={"scheduled_for": "2099-07-09T14:00:00Z"},
            )
            publish_response = await client.post(
                "/api/v1/platform-posts/1/publish-now",
            )
    finally:
        app.dependency_overrides.clear()

    assert patch_response.status_code == 200
    assert patch_response.json()["draft_caption"] == "Edited PelleVista caption."
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert schedule_response.status_code == 200
    assert schedule_response.json()["status"] == "scheduled"
    assert schedule_response.json()["scheduled_for"].startswith("2099-07-09T14:00:00")
    assert publish_response.status_code == 409
    assert publish_response.json() == {
        "detail": "Meta publishing is deferred until OAuth and token storage are ready.",
    }
    assert fake_session.posts[1].status == "scheduled"
    assert fake_session.posts[1].publish_error == (
        "Meta publishing is deferred until OAuth and token storage are ready."
    )


@pytest.mark.asyncio
async def test_platform_post_schedule_requires_approval_and_cancel_is_manual() -> None:
    fake_session = FakeManualReviewSession(posts=[_post(1), _post(2, status="approved")])

    async def override_get_session() -> FakeManualReviewSession:
        return fake_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            schedule_response = await client.post(
                "/api/v1/platform-posts/1/schedule",
                json={"scheduled_for": datetime(2099, 7, 9, 14, tzinfo=UTC).isoformat()},
            )
            cancel_response = await client.post("/api/v1/platform-posts/2/cancel")
    finally:
        app.dependency_overrides.clear()

    assert schedule_response.status_code == 409
    assert schedule_response.json() == {
        "detail": "Approve the post before scheduling it.",
    }
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"
