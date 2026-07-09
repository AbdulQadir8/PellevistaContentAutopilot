from datetime import date

from pydantic import BaseModel, Field, computed_field


class DailyContentPlanRequest(BaseModel):
    date: date
    number_of_ideas: int = Field(default=2, ge=1, le=10)


class PlatformPostDraftRead(BaseModel):
    platform: str
    draft_caption: str
    status: str = "draft"


class ContentIdeaRead(BaseModel):
    product_title: str
    pillar: str
    angle: str
    platform_post_drafts: list[PlatformPostDraftRead] = Field(default_factory=list)


class DailyContentPlanRead(BaseModel):
    date: date
    content_ideas: list[ContentIdeaRead]

    @computed_field
    @property
    def total_drafts(self) -> int:
        return sum(len(idea.platform_post_drafts) for idea in self.content_ideas)
