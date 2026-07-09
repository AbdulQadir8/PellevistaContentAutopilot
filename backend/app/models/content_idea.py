from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.brand import Brand
    from app.models.platform_post import PlatformPost
    from app.models.product import Product


class ContentIdea(SQLModel, table=True):
    __tablename__ = "content_ideas"

    id: int | None = Field(default=None, primary_key=True)
    brand_id: int = Field(foreign_key="brands.id", index=True, nullable=False)
    product_id: int | None = Field(default=None, foreign_key="products.id", index=True)
    title: str = Field(max_length=255, nullable=False)
    angle: str = Field(max_length=500, nullable=False)
    brief: str | None = Field(default=None)
    status: str = Field(default="draft", max_length=40, nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )

    brand: "Brand" = Relationship(back_populates="content_ideas")
    product: Optional["Product"] = Relationship(back_populates="content_ideas")
    platform_posts: list["PlatformPost"] = Relationship(back_populates="content_idea")
