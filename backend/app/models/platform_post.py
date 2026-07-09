from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.content_idea import ContentIdea
    from app.models.product import Product


class PlatformPost(SQLModel, table=True):
    __tablename__ = "platform_posts"

    id: int | None = Field(default=None, primary_key=True)
    content_idea_id: int = Field(
        foreign_key="content_ideas.id",
        index=True,
        nullable=False,
    )
    product_id: int | None = Field(default=None, foreign_key="products.id", index=True)
    platform: str = Field(max_length=40, nullable=False, index=True)
    status: str = Field(default="draft", max_length=40, nullable=False, index=True)
    draft_caption: str = Field(nullable=False)
    draft_media_url: str | None = Field(default=None, max_length=2048)
    external_post_id: str | None = Field(default=None, max_length=255, index=True)
    external_post_url: str | None = Field(default=None, max_length=2048)
    publish_error: str | None = Field(default=None)
    published_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
    )
    scheduled_for: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )

    content_idea: "ContentIdea" = Relationship(back_populates="platform_posts")
    product: Optional["Product"] = Relationship(back_populates="platform_posts")
