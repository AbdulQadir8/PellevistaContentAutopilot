from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.brand import Brand
    from app.models.content_idea import ContentIdea
    from app.models.platform_post import PlatformPost
    from app.models.product_image import ProductImage


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: int | None = Field(default=None, primary_key=True)
    brand_id: int = Field(foreign_key="brands.id", index=True, nullable=False)
    shopify_product_id: str = Field(max_length=128, nullable=False, unique=True)
    handle: str = Field(max_length=255, nullable=False, index=True)
    title: str = Field(max_length=255, nullable=False)
    vendor: str | None = Field(default=None, max_length=255)
    product_type: str | None = Field(default=None, max_length=255)
    status: str = Field(default="active", max_length=40, nullable=False, index=True)
    description: str | None = Field(default=None)
    tags: str | None = Field(default=None)
    price: str | None = Field(default=None, max_length=40)
    currency_code: str | None = Field(default=None, max_length=10)
    total_inventory: int | None = Field(default=None)
    available_for_sale: bool = Field(default=False, nullable=False)
    has_image: bool = Field(default=False, nullable=False)
    eligible_for_content: bool = Field(default=False, nullable=False, index=True)
    priority_score: int = Field(default=0, nullable=False, index=True)
    last_posted_at: datetime | None = Field(default=None, index=True)
    last_synced_at: datetime | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )

    brand: "Brand" = Relationship(back_populates="products")
    images: list["ProductImage"] = Relationship(back_populates="product")
    content_ideas: list["ContentIdea"] = Relationship(back_populates="product")
    platform_posts: list["PlatformPost"] = Relationship(back_populates="product")
