from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

QualityStatus = Literal["rejected", "needs_review", "approved_candidate"]
QualitySeverity = Literal["pass", "warning", "fail"]


class RecentCaptionRead(BaseModel):
    caption: str
    posted_date: date


class QualityCheckRequest(BaseModel):
    asset_file_path: str | None = None
    asset_url: str | None = None
    asset_type: Literal["image", "video"] = "image"
    expected_aspect_ratio: str
    minimum_width: int = Field(default=1080, ge=1)
    minimum_height: int = Field(default=1080, ge=1)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    caption: str
    product_url: str | None = None
    discount_active: bool = False
    check_date: date
    recent_captions: list[RecentCaptionRead] = Field(default_factory=list)


class QualityCheckItemRead(BaseModel):
    name: str
    status: QualitySeverity
    message: str
    score_delta: int


class QualityCheckResultRead(BaseModel):
    score: int
    status: QualityStatus
    manual_approval_required: bool = True
    checks: list[QualityCheckItemRead]
