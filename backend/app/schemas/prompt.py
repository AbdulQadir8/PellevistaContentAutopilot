from typing import Literal

from pydantic import BaseModel, Field

PlatformName = Literal["instagram", "pinterest", "facebook", "x"]


class PromptProductInput(BaseModel):
    title: str = Field(min_length=1)
    product_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    price: str | None = None


class PromptProductImageInput(BaseModel):
    url: str = Field(min_length=1)
    alt_text: str | None = None


class PromptBuilderInput(BaseModel):
    product: PromptProductInput
    product_image: PromptProductImageInput
    content_pillar: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    platform: PlatformName
    aspect_ratio: str | None = None
    creative_style: str = "premium editorial menswear product advertisement"


class GenerationSettings(BaseModel):
    platform: PlatformName
    aspect_ratio: str
    asset_type: Literal["image", "video"]
    creative_style: str
    reference_image_url: str
    preserve_product_identity: bool = True
    product_fidelity: Literal["strict"] = "strict"
    lighting: str
    camera_direction: str
    duration_seconds: int | None = None


class PromptBuilderOutput(BaseModel):
    higgsfield_prompt: str
    negative_prompt: str
    generation_settings: GenerationSettings

