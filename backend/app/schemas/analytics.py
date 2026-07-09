from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PostAnalyticsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform_post_id: int
    platform: str
    external_post_id: str
    external_post_url: str
    published_at: datetime
    caption: str
    product_id: int | None = None
    content_pillar: str
    collection_label: str
    collection_due_at: datetime
    collected_at: datetime | None = None
    likes: int
    comments: int
    shares: int
    saves: int
    clicks: int
    impressions: int | None = None


class AnalyticsHighlight(BaseModel):
    label: str
    value: str
    score: float = 0


class WorstPostRead(BaseModel):
    platform: str
    external_post_url: str
    caption: str
    score: float


class AnalyticsDashboardRead(BaseModel):
    total_published_posts: int
    total_snapshots: int
    pending_collections: int
    best_platform: AnalyticsHighlight
    best_product: AnalyticsHighlight
    best_hook: AnalyticsHighlight
    best_content_pillar: AnalyticsHighlight
    best_posting_time: AnalyticsHighlight
    worst_post: WorstPostRead | None = None
    next_action: str
