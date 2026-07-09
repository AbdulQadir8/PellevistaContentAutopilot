from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel

from app.core.database import get_session
from app.main import app
from app.models import ContentIdea, GenerationJob
from app.services.higgsfield import GenerationJobService, HiggsfieldGenerator


class FakeController:
    request_id = "hf-request-123"

    async def get(self) -> dict[str, object]:
        return {
            "output": [
                {"url": "https://cdn.higgsfield.example/generated-shoe.mp4"},
            ],
        }


class FakeHiggsfieldClient:
    def __init__(self) -> None:
        self.arguments: dict[str, object] | None = None

    async def submit(
        self,
        application: str,
        arguments: dict[str, object],
    ) -> FakeController:
        self.arguments = arguments
        return FakeController()


class FakeGenerationSession:
    def __init__(self, content_idea: ContentIdea | None) -> None:
        self.content_idea = content_idea
        self.created_job: GenerationJob | None = None

    async def get(self, model: type[object], entity_id: int) -> ContentIdea | None:
        if model is ContentIdea and self.content_idea and entity_id == self.content_idea.id:
            return self.content_idea

        return None

    def add(self, model: object) -> None:
        if isinstance(model, GenerationJob):
            self.created_job = model

    async def commit(self) -> None:
        return None

    async def refresh(self, model: object) -> None:
        return None


def test_generation_tables_are_registered() -> None:
    assert {"generation_jobs", "generated_assets"}.issubset(SQLModel.metadata.tables)


@pytest.mark.asyncio
async def test_higgsfield_generator_submits_prompt_and_extracts_result_url() -> None:
    fake_client = FakeHiggsfieldClient()
    result = await HiggsfieldGenerator(
        client=fake_client,  # type: ignore[arg-type]
        application="test-application",
    ).generate(
        prompt="Preserve the exact shoe identity.",
        reference_image_url="https://cdn.example.com/reference.jpg",
        aspect_ratio="9:16",
    )

    assert result.request_id == "hf-request-123"
    assert result.result_url == "https://cdn.higgsfield.example/generated-shoe.mp4"
    assert fake_client.arguments == {
        "prompt": "Preserve the exact shoe identity.",
        "reference_image_url": "https://cdn.example.com/reference.jpg",
        "aspect_ratio": "9:16",
    }


@pytest.mark.asyncio
async def test_generate_content_idea_route_returns_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeGenerationSession(
        ContentIdea(
            id=1,
            brand_id=1,
            product_id=1,
            title="Pain-point hook",
            angle="A formal outfit is not complete until the shoes look intentional.",
        ),
    )
    enqueued_job_ids: list[UUID] = []

    async def override_get_session() -> FakeGenerationSession:
        return fake_session

    def fake_enqueue(self: GenerationJobService, job_id: UUID) -> None:
        enqueued_job_ids.append(job_id)

    monkeypatch.setattr(GenerationJobService, "enqueue", fake_enqueue)
    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/content-ideas/1/generate",
                json={
                    "platform": "instagram",
                    "creative_style": "premium studio video",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"
    assert fake_session.created_job is not None
    assert str(fake_session.created_job.id) == payload["job_id"]
    assert fake_session.created_job.aspect_ratio == "9:16"
    assert fake_session.created_job.asset_type == "video"
    assert enqueued_job_ids == [fake_session.created_job.id]


@pytest.mark.asyncio
async def test_generate_content_idea_route_returns_404_for_missing_idea() -> None:
    async def override_get_session() -> FakeGenerationSession:
        return FakeGenerationSession(None)

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post("/api/v1/content-ideas/999/generate")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Content idea not found."}

