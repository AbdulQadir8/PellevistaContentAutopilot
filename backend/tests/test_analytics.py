from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel

from app.core.database import get_session
from app.main import app
from app.models import ContentIdea, PlatformPost, PostAnalytics, Product
from app.services.analytics import AnalyticsMetrics, AnalyticsService


class FakeResult:
    def __init__(self, rows: list[PostAnalytics]) -> None:
        self.rows = rows

    def all(self) -> list[PostAnalytics]:
        return self.rows


class FakeMetricCollector:
    async def collect(self, snapshot: PostAnalytics) -> AnalyticsMetrics:
        return AnalyticsMetrics(
            likes=10,
            comments=2,
            shares=3,
            saves=4,
            clicks=5,
            impressions=1000,
        )


class FakeAnalyticsSession:
    def __init__(
        self,
        snapshots: list[PostAnalytics] | None = None,
        content_idea: ContentIdea | None = None,
        products: list[Product] | None = None,
    ) -> None:
        self.snapshots = snapshots or []
        self.content_idea = content_idea
        self.products = {product.id: product for product in products or []}
        self.added: list[PostAnalytics] = []
        self.commits = 0

    async def get(self, model: type[object], entity_id: int) -> object | None:
        if model is ContentIdea and self.content_idea and entity_id == self.content_idea.id:
            return self.content_idea
        if model is Product:
            return self.products.get(entity_id)

        return None

    def add(self, model: object) -> None:
        if isinstance(model, PostAnalytics):
            self.added.append(model)
            self.snapshots.append(model)

    async def exec(self, statement: object) -> FakeResult:
        return FakeResult(self.snapshots)

    async def commit(self) -> None:
        self.commits += 1


def _published_post() -> PlatformPost:
    return PlatformPost(
        id=10,
        content_idea_id=5,
        product_id=3,
        platform="pinterest",
        status="published",
        draft_caption=(
            "Most men spend hundreds on a suit, then ruin the look with cheap shoes.\n\n"
            "PelleVista handcrafted leather shoes are made to finish the outfit properly."
        ),
        external_post_id="pin-123",
        external_post_url="https://www.pinterest.com/pin/pin-123/",
        published_at=datetime(2026, 7, 9, 13, 0, tzinfo=UTC),
    )


def _snapshot(
    *,
    platform_post_id: int,
    platform: str,
    score_seed: int,
    product_id: int,
    content_pillar: str,
    caption: str,
    published_at: datetime,
    collected: bool = True,
) -> PostAnalytics:
    return PostAnalytics(
        id=platform_post_id,
        platform_post_id=platform_post_id,
        platform=platform,
        external_post_id=f"external-{platform_post_id}",
        external_post_url=f"https://example.com/post/{platform_post_id}",
        published_at=published_at,
        caption=caption,
        product_id=product_id,
        content_pillar=content_pillar,
        collection_label="24h",
        collection_due_at=published_at + timedelta(days=1),
        collected_at=published_at + timedelta(days=1) if collected else None,
        likes=score_seed,
        comments=score_seed // 2,
        shares=score_seed // 3,
        saves=score_seed // 4,
        clicks=score_seed // 5,
        impressions=score_seed * 100,
    )


def test_post_analytics_table_is_registered() -> None:
    assert "post_analytics" in SQLModel.metadata.tables


@pytest.mark.asyncio
async def test_record_published_post_creates_baseline_and_collection_jobs() -> None:
    session = FakeAnalyticsSession(
        content_idea=ContentIdea(
            id=5,
            brand_id=1,
            product_id=3,
            title="Pain-point hook",
            angle="Cheap shoes make expensive clothes look average.",
        ),
    )

    snapshots = await AnalyticsService(
        session,  # type: ignore[arg-type]
    ).record_published_post(_published_post())

    assert [snapshot.collection_label for snapshot in snapshots] == [
        "published",
        "1h",
        "24h",
        "72h",
        "7d",
    ]
    assert [snapshot.collection_due_at for snapshot in snapshots] == [
        datetime(2026, 7, 9, 13, 0, tzinfo=UTC),
        datetime(2026, 7, 9, 14, 0, tzinfo=UTC),
        datetime(2026, 7, 10, 13, 0, tzinfo=UTC),
        datetime(2026, 7, 12, 13, 0, tzinfo=UTC),
        datetime(2026, 7, 16, 13, 0, tzinfo=UTC),
    ]
    assert snapshots[0].collected_at == datetime(2026, 7, 9, 13, 0, tzinfo=UTC)
    assert snapshots[1].collected_at is None
    assert all(snapshot.content_pillar == "Pain-point hook" for snapshot in snapshots)
    assert len(session.added) == 5


@pytest.mark.asyncio
async def test_collect_due_analytics_updates_metric_fields() -> None:
    snapshot = _snapshot(
        platform_post_id=1,
        platform="x",
        score_seed=0,
        product_id=1,
        content_pillar="Style education",
        caption="A formal outfit is not complete until the shoes look intentional.",
        published_at=datetime(2026, 7, 9, 14, 0, tzinfo=UTC),
        collected=False,
    )
    session = FakeAnalyticsSession(snapshots=[snapshot])

    count = await AnalyticsService(
        session,  # type: ignore[arg-type]
        metric_collector=FakeMetricCollector(),  # type: ignore[arg-type]
    ).collect_due_snapshots(now=datetime(2026, 7, 10, 14, 0, tzinfo=UTC))

    assert count == 1
    assert snapshot.likes == 10
    assert snapshot.comments == 2
    assert snapshot.shares == 3
    assert snapshot.saves == 4
    assert snapshot.clicks == 5
    assert snapshot.impressions == 1000
    assert snapshot.collected_at == datetime(2026, 7, 10, 14, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_analytics_dashboard_summarizes_best_and_worst() -> None:
    product = Product(
        id=3,
        brand_id=1,
        shopify_product_id="gid://shopify/Product/3",
        handle="black-oxford-red-sole-shoes",
        title="Black Oxford Red Sole Shoes",
    )
    snapshots = [
        _snapshot(
            platform_post_id=1,
            platform="pinterest",
            score_seed=80,
            product_id=3,
            content_pillar="Pain-point hook",
            caption="Most men spend hundreds on a suit, then ruin the look with cheap shoes.",
            published_at=datetime(2026, 7, 9, 13, 0, tzinfo=UTC),
        ),
        _snapshot(
            platform_post_id=2,
            platform="x",
            score_seed=5,
            product_id=3,
            content_pillar="Style education",
            caption="A formal outfit is not complete until the shoes look intentional.",
            published_at=datetime(2026, 7, 9, 14, 0, tzinfo=UTC),
        ),
    ]
    session = FakeAnalyticsSession(snapshots=snapshots, products=[product])

    dashboard = await AnalyticsService(session).dashboard()  # type: ignore[arg-type]

    assert dashboard.total_published_posts == 2
    assert dashboard.total_snapshots == 2
    assert dashboard.pending_collections == 0
    assert dashboard.best_platform.label == "pinterest"
    assert dashboard.best_product.label == "Black Oxford Red Sole Shoes"
    assert dashboard.best_hook.label == (
        "Most men spend hundreds on a suit, then ruin the look with cheap shoes."
    )
    assert dashboard.best_content_pillar.label == "Pain-point hook"
    assert dashboard.best_posting_time.label == "13:00 UTC"
    assert dashboard.worst_post is not None
    assert dashboard.worst_post.platform == "x"
    assert dashboard.next_action == (
        "Create another Pain-point hook post for pinterest using a similar hook."
    )


@pytest.mark.asyncio
async def test_analytics_dashboard_endpoint() -> None:
    session = FakeAnalyticsSession()

    async def override_get_session() -> FakeAnalyticsSession:
        return session

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/v1/analytics/dashboard")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["next_action"] == "Publish posts to start collecting analytics."
