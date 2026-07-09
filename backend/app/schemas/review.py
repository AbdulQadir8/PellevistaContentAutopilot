from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

WorkflowStatus = Literal[
    "draft",
    "generated",
    "needs_review",
    "approved",
    "scheduled",
    "publishing",
    "published",
    "failed",
    "cancelled",
]


class AssetReviewActionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class GeneratedAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    generation_job_id: UUID
    content_idea_id: int
    platform: str
    asset_type: str
    source_url: str
    storage_url: str
    storage_key: str | None = None
    thumbnail_url: str | None = None
    thumbnail_storage_key: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    status: WorkflowStatus
    review_note: str | None = None
    created_at: datetime
    updated_at: datetime


class PlatformPostUpdate(BaseModel):
    draft_caption: str | None = Field(default=None, min_length=1)
    draft_media_url: str | None = Field(default=None, max_length=2048)
    scheduled_for: datetime | None = None
    status: WorkflowStatus | None = None


class PlatformPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_idea_id: int
    product_id: int | None = None
    platform: str
    status: WorkflowStatus
    draft_caption: str
    draft_media_url: str | None = None
    external_post_id: str | None = None
    external_post_url: str | None = None
    publish_error: str | None = None
    published_at: datetime | None = None
    scheduled_for: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PlatformPostScheduleRequest(BaseModel):
    scheduled_for: datetime
