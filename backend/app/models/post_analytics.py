from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class PostAnalytics(SQLModel, table=True):
    __tablename__ = "post_analytics"

    id: int | None = Field(default=None, primary_key=True)
    platform_post_id: int = Field(
        foreign_key="platform_posts.id",
        index=True,
        nullable=False,
    )
    platform: str = Field(max_length=40, nullable=False, index=True)
    external_post_id: str = Field(max_length=255, nullable=False, index=True)
    external_post_url: str = Field(max_length=2048, nullable=False)
    published_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    caption: str = Field(nullable=False)
    product_id: int | None = Field(default=None, foreign_key="products.id", index=True)
    content_pillar: str = Field(max_length=255, nullable=False, index=True)
    collection_label: str = Field(max_length=40, nullable=False, index=True)
    collection_due_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    collected_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
    )
    likes: int = Field(default=0, nullable=False)
    comments: int = Field(default=0, nullable=False)
    shares: int = Field(default=0, nullable=False)
    saves: int = Field(default=0, nullable=False)
    clicks: int = Field(default=0, nullable=False)
    impressions: int | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
