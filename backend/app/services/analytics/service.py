from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import ContentIdea, PlatformPost, PostAnalytics, Product
from app.schemas import AnalyticsDashboardRead, AnalyticsHighlight, WorstPostRead
from app.services.analytics.metrics import AnalyticsMetricCollector

ANALYTICS_CHECKPOINTS: tuple[tuple[str, timedelta], ...] = (
    ("published", timedelta()),
    ("1h", timedelta(hours=1)),
    ("24h", timedelta(hours=24)),
    ("72h", timedelta(hours=72)),
    ("7d", timedelta(days=7)),
)


@dataclass(frozen=True, slots=True)
class ScoredAnalytics:
    snapshot: PostAnalytics
    score: float


class AnalyticsService:
    def __init__(
        self,
        session: AsyncSession,
        metric_collector: AnalyticsMetricCollector | None = None,
    ) -> None:
        self.session = session
        self.metric_collector = metric_collector or AnalyticsMetricCollector()

    async def record_published_post(self, post: PlatformPost) -> list[PostAnalytics]:
        if post.id is None:
            raise ValueError("Platform post must be persisted before analytics.")
        if not post.external_post_id or not post.external_post_url:
            raise ValueError("Published post must have external post fields.")

        published_at = self._normalize_datetime(post.published_at or datetime.now(UTC))
        post.published_at = published_at
        content_pillar = await self._content_pillar(post.content_idea_id)
        snapshots: list[PostAnalytics] = []

        for label, offset in ANALYTICS_CHECKPOINTS:
            collected_at = published_at if label == "published" else None
            snapshot = PostAnalytics(
                platform_post_id=post.id,
                platform=post.platform.lower(),
                external_post_id=post.external_post_id,
                external_post_url=post.external_post_url,
                published_at=published_at,
                caption=post.draft_caption,
                product_id=post.product_id,
                content_pillar=content_pillar,
                collection_label=label,
                collection_due_at=published_at + offset,
                collected_at=collected_at,
            )
            self.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    async def collect_due_snapshots(
        self,
        now: datetime | None = None,
    ) -> int:
        due_at = self._normalize_datetime(now or datetime.now(UTC))
        result = await self.session.exec(
            select(PostAnalytics)
            .where(col(PostAnalytics.collected_at).is_(None))
            .where(PostAnalytics.collection_due_at <= due_at)
            .order_by(col(PostAnalytics.collection_due_at), col(PostAnalytics.id)),
        )
        snapshots = result.all()

        for snapshot in snapshots:
            metrics = await self.metric_collector.collect(snapshot)
            snapshot.likes = metrics.likes
            snapshot.comments = metrics.comments
            snapshot.shares = metrics.shares
            snapshot.saves = metrics.saves
            snapshot.clicks = metrics.clicks
            snapshot.impressions = metrics.impressions
            snapshot.collected_at = due_at

        await self.session.commit()
        return len(snapshots)

    async def dashboard(self) -> AnalyticsDashboardRead:
        snapshots = await self._load_snapshots()
        scored = [
            ScoredAnalytics(snapshot=snapshot, score=self._score(snapshot))
            for snapshot in snapshots
        ]
        collected = [item for item in scored if item.snapshot.collected_at is not None]
        scored_source = collected or scored
        pending_collections = sum(
            1 for snapshot in snapshots if snapshot.collected_at is None
        )
        total_posts = len({snapshot.platform_post_id for snapshot in snapshots})
        product_names = await self._product_names(
            snapshot.product_id for snapshot in snapshots if snapshot.product_id is not None
        )

        return AnalyticsDashboardRead(
            total_published_posts=total_posts,
            total_snapshots=len(snapshots),
            pending_collections=pending_collections,
            best_platform=self._best_group(
                scored_source,
                lambda item: item.snapshot.platform,
                empty_label="No platform data",
            ),
            best_product=self._best_group(
                scored_source,
                lambda item: product_names.get(
                    item.snapshot.product_id,
                    "Unknown product",
                ),
                empty_label="No product data",
            ),
            best_hook=self._best_group(
                scored_source,
                lambda item: self._hook(item.snapshot.caption),
                empty_label="No hook data",
            ),
            best_content_pillar=self._best_group(
                scored_source,
                lambda item: item.snapshot.content_pillar,
                empty_label="No pillar data",
            ),
            best_posting_time=self._best_group(
                scored_source,
                lambda item: item.snapshot.published_at.strftime("%H:00 UTC"),
                empty_label="No posting time data",
            ),
            worst_post=self._worst_post(scored_source),
            next_action=self._next_action(scored_source, pending_collections),
        )

    async def _load_snapshots(self) -> list[PostAnalytics]:
        result = await self.session.exec(
            select(PostAnalytics).order_by(
                col(PostAnalytics.published_at).desc(),
                col(PostAnalytics.collection_due_at).desc(),
            ),
        )
        return list(result.all())

    async def _content_pillar(self, content_idea_id: int) -> str:
        content_idea = await self.session.get(ContentIdea, content_idea_id)
        if content_idea is None:
            return "Unknown"

        return content_idea.title

    async def _product_names(self, product_ids: Iterable[int]) -> dict[int | None, str]:
        names: dict[int | None, str] = {}
        for product_id in set(product_ids):
            product = await self.session.get(Product, product_id)
            if product is not None:
                names[product_id] = product.title

        return names

    @staticmethod
    def _best_group(
        items: list[ScoredAnalytics],
        key: Callable[[ScoredAnalytics], str],
        empty_label: str,
    ) -> AnalyticsHighlight:
        if not items:
            return AnalyticsHighlight(label=empty_label, value="No data", score=0)

        grouped: dict[str, float] = defaultdict(float)
        for item in items:
            grouped[key(item)] += item.score

        label, score = max(grouped.items(), key=lambda entry: (entry[1], entry[0]))
        return AnalyticsHighlight(label=label, value=label, score=round(score, 2))

    @staticmethod
    def _worst_post(items: list[ScoredAnalytics]) -> WorstPostRead | None:
        if not items:
            return None

        worst = min(items, key=lambda item: (item.score, item.snapshot.published_at))
        return WorstPostRead(
            platform=worst.snapshot.platform,
            external_post_url=worst.snapshot.external_post_url,
            caption=worst.snapshot.caption,
            score=round(worst.score, 2),
        )

    @staticmethod
    def _next_action(items: list[ScoredAnalytics], pending_collections: int) -> str:
        if pending_collections:
            return "Collect due analytics snapshots before changing the plan."
        if not items:
            return "Publish posts to start collecting analytics."

        best = max(items, key=lambda item: (item.score, item.snapshot.platform))
        return (
            f"Create another {best.snapshot.content_pillar} post for "
            f"{best.snapshot.platform} using a similar hook."
        )

    @staticmethod
    def _score(snapshot: PostAnalytics) -> float:
        return (
            snapshot.likes
            + snapshot.comments * 2
            + snapshot.shares * 3
            + snapshot.saves * 3
            + snapshot.clicks * 2
            + (snapshot.impressions or 0) * 0.01
        )

    @staticmethod
    def _hook(caption: str) -> str:
        for line in caption.splitlines():
            clean_line = line.strip()
            if clean_line and not clean_line.endswith(":"):
                return clean_line[:160]

        return "No hook"

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)
