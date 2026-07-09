from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.content_idea import ContentIdea
    from app.models.product import Product


class Brand(SQLModel, table=True):
    __tablename__ = "brands"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, nullable=False)
    slug: str = Field(max_length=120, nullable=False, unique=True, index=True)
    shopify_domain: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )

    products: list["Product"] = Relationship(back_populates="brand")
    content_ideas: list["ContentIdea"] = Relationship(back_populates="brand")
