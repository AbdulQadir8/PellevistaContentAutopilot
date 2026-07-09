from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.product import Product


class ProductImage(SQLModel, table=True):
    __tablename__ = "product_images"

    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True, nullable=False)
    shopify_image_id: str | None = Field(default=None, max_length=128, unique=True)
    url: str = Field(max_length=2048, nullable=False)
    alt_text: str | None = Field(default=None, max_length=500)
    position: int = Field(default=0, nullable=False)
    width: int | None = Field(default=None)
    height: int | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )

    product: "Product" = Relationship(back_populates="images")
