from dataclasses import dataclass

from app.models import PostAnalytics


@dataclass(frozen=True, slots=True)
class AnalyticsMetrics:
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    impressions: int | None = None


class AnalyticsMetricCollector:
    async def collect(self, snapshot: PostAnalytics) -> AnalyticsMetrics:
        return AnalyticsMetrics()
