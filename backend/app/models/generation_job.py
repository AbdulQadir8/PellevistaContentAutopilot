from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.generated_asset import GeneratedAsset


class GenerationJob(SQLModel, table=True):
    __tablename__ = "generation_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    content_idea_id: int = Field(
        foreign_key="content_ideas.id",
        index=True,
        nullable=False,
    )
    platform: str = Field(max_length=40, nullable=False, index=True)
    status: str = Field(default="accepted", max_length=40, nullable=False, index=True)
    prompt: str | None = Field(default=None)
    negative_prompt: str | None = Field(default=None)
    reference_image_url: str | None = Field(default=None, max_length=2048)
    aspect_ratio: str = Field(max_length=20, nullable=False)
    asset_type: str = Field(max_length=40, nullable=False)
    creative_style: str = Field(max_length=255, nullable=False)
    higgsfield_request_id: str | None = Field(default=None, max_length=255)
    higgsfield_result_url: str | None = Field(default=None, max_length=2048)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(default=None)

    generated_assets: list["GeneratedAsset"] = Relationship(back_populates="job")

