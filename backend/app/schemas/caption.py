from typing import Literal

from pydantic import BaseModel, Field

CaptionPlatform = Literal["x", "facebook", "instagram", "pinterest"]


class CaptionGeneratorInput(BaseModel):
    product_title: str = Field(min_length=1)
    product_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    pillar: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    platform: CaptionPlatform


class CaptionGeneratorOutput(BaseModel):
    platform: CaptionPlatform
    caption: str
    title: str | None = None
    description: str | None = None
    hashtags: list[str] = Field(default_factory=list)

