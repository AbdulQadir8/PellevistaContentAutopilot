from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.generation_job import GenerationJob


class GeneratedAsset(SQLModel, table=True):
    __tablename__ = "generated_assets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    generation_job_id: UUID = Field(
        foreign_key="generation_jobs.id",
        index=True,
        nullable=False,
    )
    content_idea_id: int = Field(
        foreign_key="content_ideas.id",
        index=True,
        nullable=False,
    )
    platform: str = Field(max_length=40, nullable=False, index=True)
    asset_type: str = Field(max_length=40, nullable=False)
    source_url: str = Field(max_length=2048, nullable=False)
    storage_url: str = Field(max_length=2048, nullable=False)
    storage_key: str | None = Field(default=None, max_length=1024)
    thumbnail_url: str | None = Field(default=None, max_length=2048)
    thumbnail_storage_key: str | None = Field(default=None, max_length=1024)
    mime_type: str | None = Field(default=None, max_length=120)
    file_size_bytes: int | None = Field(default=None)
    status: str = Field(default="generated", max_length=40, nullable=False, index=True)
    review_note: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    job: "GenerationJob" = Relationship(back_populates="generated_assets")
