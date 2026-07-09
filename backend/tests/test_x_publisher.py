import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from app.models import PlatformPost, PostAnalytics, PublishAttempt
from app.services.publishers.x import XPublisher, XPublishError


@dataclass
class FakeResponse:
    payload: dict[str, Any]
    content: bytes = b""
    headers: dict[str, str] | None = None
    status_code: int = 200

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeXHttpClient:
    def __init__(
        self,
        media_type: str = "image/png",
        create_status_codes: list[int] | None = None,
    ) -> None:
        self.media_type = media_type
        self.create_status_codes = create_status_codes or []
        self.get_urls: list[str] = []
        self.post_calls: list[dict[str, Any]] = []

    async def get(self, url: str) -> FakeResponse:
        self.get_urls.append(url)
        return FakeResponse(
            payload={},
            content=b"fake-image",
            headers={"content-type": self.media_type},
        )

    async def post(
        self,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> FakeResponse:
        self.post_calls.append({"url": url, "headers": headers, "json": json})
        if url.endswith("/2/media/upload"):
            return FakeResponse(payload={"data": {"id": "media-123"}})

        status_code = self.create_status_codes.pop(0) if self.create_status_codes else 200
        if status_code >= 400:
            return FakeResponse(payload={"errors": []}, status_code=status_code)

        return FakeResponse(payload={"data": {"id": "tweet-456", "text": json["text"]}})


class FakeXSession:
    def __init__(self, post: PlatformPost) -> None:
        self.post = post
        self.commits = 0
        self.analytics: list[PostAnalytics] = []
        self.attempts: dict[str, PublishAttempt] = {}

    async def get(self, model: type[object], entity_id: object) -> object | None:
        if model is PlatformPost and entity_id == self.post.id:
            return self.post
        if model is PublishAttempt and isinstance(entity_id, str):
            return self.attempts.get(entity_id)

        return None

    def add(self, model: object) -> None:
        if isinstance(model, PostAnalytics):
            self.analytics.append(model)
        if isinstance(model, PublishAttempt):
            self.attempts[model.idempotency_key] = model

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, model: object) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _x_post(**overrides: object) -> PlatformPost:
    values = {
        "id": 1,
        "content_idea_id": 1,
        "product_id": 1,
        "platform": "x",
        "status": "publishing",
        "draft_caption": "PelleVista handcrafted leather shoes finish the outfit.",
        "draft_media_url": "https://cdn.pellevista.example/x-post.png",
        "scheduled_for": datetime(2026, 7, 9, 14, tzinfo=UTC),
    }
    values.update(overrides)
    return PlatformPost(**values)


def test_publish_attempt_uses_required_idempotency_constraint() -> None:
    constraint = next(
        item
        for item in PublishAttempt.__table__.constraints
        if item.name == "uq_publish_attempt_post_platform_scheduled_at"
    )

    assert [column.name for column in constraint.columns] == [
        "platform_post_id",
        "platform",
        "scheduled_at",
    ]


@pytest.mark.asyncio
async def test_x_publisher_uploads_image_creates_post_and_marks_published() -> None:
    post = _x_post()
    session = FakeXSession(post)
    client = FakeXHttpClient()

    published_post = await XPublisher(
        session=session,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
        access_token="x-token",
        api_base_url="https://api.x.test",
        public_post_base_url="https://x.test/i/web/status",
    ).publish_post(1)

    assert client.get_urls == ["https://cdn.pellevista.example/x-post.png"]
    assert client.post_calls[0] == {
        "url": "https://api.x.test/2/media/upload",
        "headers": {
            "Authorization": "Bearer x-token",
            "Content-Type": "application/json",
        },
        "json": {
            "media": base64.b64encode(b"fake-image").decode("ascii"),
            "media_category": "tweet_image",
            "media_type": "image/png",
            "shared": False,
        },
    }
    assert client.post_calls[1] == {
        "url": "https://api.x.test/2/tweets",
        "headers": {
            "Authorization": "Bearer x-token",
            "Content-Type": "application/json",
        },
        "json": {
            "text": "PelleVista handcrafted leather shoes finish the outfit.",
            "media": {"media_ids": ["media-123"]},
        },
    }
    assert published_post.status == "published"
    assert published_post.published_at is not None
    assert published_post.external_post_id == "tweet-456"
    assert published_post.external_post_url == "https://x.test/i/web/status/tweet-456"
    assert published_post.publish_error is None
    assert [snapshot.collection_label for snapshot in session.analytics] == [
        "published",
        "1h",
        "24h",
        "72h",
        "7d",
    ]


@pytest.mark.asyncio
async def test_x_publisher_idempotency_prevents_duplicate_publish() -> None:
    post = _x_post(status="scheduled")
    session = FakeXSession(post)
    client = FakeXHttpClient()
    publisher = XPublisher(
        session=session,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
        access_token="x-token",
        api_base_url="https://api.x.test",
        public_post_base_url="https://x.test/i/web/status",
    )

    await publisher.publish_post(1)
    assert len(client.post_calls) == 2

    post.status = "scheduled"
    post.external_post_id = None
    post.external_post_url = None
    post.published_at = None

    published_post = await publisher.publish_post(1)

    assert len(client.post_calls) == 2
    assert len(session.analytics) == 5
    assert published_post.status == "published"
    assert published_post.external_post_id == "tweet-456"
    assert published_post.external_post_url == "https://x.test/i/web/status/tweet-456"
    assert list(session.attempts.values())[0].status == "published"


@pytest.mark.asyncio
async def test_x_publisher_retries_failed_publish_with_same_idempotency_key() -> None:
    post = _x_post(status="scheduled")
    session = FakeXSession(post)
    client = FakeXHttpClient(create_status_codes=[500, 200])
    publisher = XPublisher(
        session=session,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
        access_token="x-token",
        api_base_url="https://api.x.test",
        public_post_base_url="https://x.test/i/web/status",
    )

    with pytest.raises(RuntimeError, match="HTTP 500"):
        await publisher.publish_post(1)

    failed_attempt = list(session.attempts.values())[0]
    assert post.status == "failed"
    assert failed_attempt.status == "failed"
    assert failed_attempt.attempt_count == 1

    await publisher.publish_post(1)

    retried_attempt = list(session.attempts.values())[0]
    assert post.status == "published"
    assert retried_attempt.status == "published"
    assert retried_attempt.attempt_count == 2
    assert [call["url"] for call in client.post_calls] == [
        "https://api.x.test/2/media/upload",
        "https://api.x.test/2/tweets",
        "https://api.x.test/2/media/upload",
        "https://api.x.test/2/tweets",
    ]


@pytest.mark.asyncio
async def test_x_publisher_marks_expired_token_failure_without_publishing() -> None:
    post = _x_post(status="scheduled")
    session = FakeXSession(post)
    client = FakeXHttpClient(create_status_codes=[401])

    with pytest.raises(RuntimeError, match="HTTP 401"):
        await XPublisher(
            session=session,  # type: ignore[arg-type]
            client=client,  # type: ignore[arg-type]
            access_token="expired-token",
            api_base_url="https://api.x.test",
        ).publish_post(1)

    failed_attempt = list(session.attempts.values())[0]
    assert post.status == "failed"
    assert post.external_post_id is None
    assert post.publish_error == "HTTP 401"
    assert failed_attempt.status == "failed"
    assert failed_attempt.error_message == "HTTP 401"


@pytest.mark.asyncio
async def test_x_publisher_rejects_video_media_in_v1_and_marks_failed() -> None:
    post = _x_post(draft_media_url="https://cdn.pellevista.example/x-video.mp4")
    session = FakeXSession(post)
    client = FakeXHttpClient(media_type="video/mp4")

    with pytest.raises(XPublishError, match="Only image media is supported"):
        await XPublisher(
            session=session,  # type: ignore[arg-type]
            client=client,  # type: ignore[arg-type]
            access_token="x-token",
        ).publish_post(1)

    assert post.status == "failed"
    assert post.publish_error == "Only image media is supported for X publishing in v1."
    assert len(client.post_calls) == 0


@pytest.mark.asyncio
async def test_x_publisher_rejects_empty_caption_before_external_calls() -> None:
    post = _x_post(draft_caption="   ")
    session = FakeXSession(post)
    client = FakeXHttpClient()

    with pytest.raises(XPublishError, match="X caption cannot be empty"):
        await XPublisher(
            session=session,  # type: ignore[arg-type]
            client=client,  # type: ignore[arg-type]
            access_token="x-token",
        ).publish_post(1)

    assert post.status == "failed"
    assert post.publish_error == "X caption cannot be empty."
    assert client.get_urls == []
    assert client.post_calls == []
