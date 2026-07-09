from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.main import app
from app.models import PlatformPost
from app.services.publishers import (
    FacebookPublisher,
    InstagramPublisher,
    META_DEFERRED_MESSAGE,
    MetaOAuthService,
    MetaPublishingDeferredError,
)
from app.services.scheduler import SchedulerService


class FakeResult:
    def __init__(self, posts: list[PlatformPost]) -> None:
        self.posts = posts

    def all(self) -> list[PlatformPost]:
        return self.posts


class FakeMetaSession:
    def __init__(self, posts: list[PlatformPost]) -> None:
        self.posts = {post.id: post for post in posts if post.id is not None}
        self.commits = 0

    async def get(self, model: type[object], entity_id: int) -> object | None:
        if model is PlatformPost:
            return self.posts.get(entity_id)

        return None

    async def exec(self, statement: object) -> FakeResult:
        return FakeResult(list(self.posts.values()))

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, model: object) -> None:
        return None


def _meta_post(platform: str = "instagram") -> PlatformPost:
    return PlatformPost(
        id=1,
        content_idea_id=1,
        product_id=1,
        platform=platform,
        status="scheduled",
        draft_caption="A sharp suit deserves shoes that match the effort.",
        scheduled_for=datetime(2026, 7, 9, 13, 20, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_meta_publishers_and_oauth_are_explicitly_deferred() -> None:
    with pytest.raises(MetaPublishingDeferredError, match=META_DEFERRED_MESSAGE):
        MetaOAuthService().authorization_url()

    with pytest.raises(MetaPublishingDeferredError, match=META_DEFERRED_MESSAGE):
        await MetaOAuthService().exchange_code("code")

    with pytest.raises(MetaPublishingDeferredError, match=META_DEFERRED_MESSAGE):
        await InstagramPublisher().publish_post(1)

    with pytest.raises(MetaPublishingDeferredError, match=META_DEFERRED_MESSAGE):
        await FacebookPublisher().publish_post(1)


@pytest.mark.asyncio
async def test_publish_now_for_meta_post_returns_deferred_conflict() -> None:
    post = _meta_post("facebook")
    fake_session = FakeMetaSession(posts=[post])

    async def override_get_session() -> FakeMetaSession:
        return fake_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post("/api/v1/platform-posts/1/publish-now")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {"detail": META_DEFERRED_MESSAGE}
    assert post.status == "scheduled"
    assert post.publish_error == META_DEFERRED_MESSAGE


@pytest.mark.asyncio
async def test_scheduler_does_not_move_due_meta_posts_to_publishing() -> None:
    post = _meta_post("instagram")
    fake_session = FakeMetaSession(posts=[post])

    count = await SchedulerService(
        fake_session,  # type: ignore[arg-type]
    ).publish_due_scheduled_posts(now=datetime(2026, 7, 9, 13, 30, tzinfo=UTC))

    assert count == 1
    assert post.status == "scheduled"
    assert post.publish_error == META_DEFERRED_MESSAGE
