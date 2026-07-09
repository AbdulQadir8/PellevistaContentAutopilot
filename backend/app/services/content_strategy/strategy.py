from datetime import date

from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas import ContentIdeaRead, DailyContentPlanRead, PlatformPostDraftRead
from app.schemas.caption import CaptionPlatform
from app.services.captions import CaptionGeneratorService
from app.services.content_strategy.product_selection import ProductSelectionService
from app.services.content_strategy.templates import (
    CONTENT_PILLARS,
    PAIN_POINT_HOOKS,
    PILLAR_ANGLES,
    PLATFORMS,
)


class ContentStrategyService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.selection_service = ProductSelectionService(session)
        self.caption_generator = CaptionGeneratorService()

    async def create_daily_plan(
        self,
        plan_date: date,
        number_of_ideas: int = 2,
    ) -> DailyContentPlanRead:
        selected_ideas = await self.selection_service.select_for_daily_content(
            plan_date=plan_date,
            number_of_ideas=number_of_ideas,
        )
        content_ideas = [
            self._build_content_idea(idea, index)
            for index, idea in enumerate(selected_ideas)
        ]

        return DailyContentPlanRead(
            date=plan_date,
            content_ideas=content_ideas,
        )

    def _build_content_idea(
        self,
        idea: ContentIdeaRead,
        index: int,
    ) -> ContentIdeaRead:
        pillar = self._pillar_for_idea(idea=idea, index=index)
        angle = self._angle_for_pillar(
            pillar=pillar,
            product_title=idea.product_title,
            fallback_angle=idea.angle,
            index=index,
        )

        return ContentIdeaRead(
            product_title=idea.product_title,
            pillar=pillar,
            angle=angle,
            platform_post_drafts=[
                self._platform_draft(
                    platform=platform,
                    product_title=idea.product_title,
                    pillar=pillar,
                    angle=angle,
                )
                for platform in PLATFORMS
            ],
        )

    @staticmethod
    def _pillar_for_idea(idea: ContentIdeaRead, index: int) -> str:
        if idea.pillar in CONTENT_PILLARS:
            return idea.pillar

        return CONTENT_PILLARS[index % len(CONTENT_PILLARS)]

    @staticmethod
    def _angle_for_pillar(
        pillar: str,
        product_title: str,
        fallback_angle: str,
        index: int,
    ) -> str:
        if pillar == "Pain-point hook":
            return PAIN_POINT_HOOKS[index % len(PAIN_POINT_HOOKS)]

        if pillar == "Red-sole positioning":
            return (
                f"Use the red sole on {product_title} as the detail that makes the "
                "whole outfit feel intentional."
            )

        options = PILLAR_ANGLES.get(pillar)
        if options:
            return options[index % len(options)]

        return fallback_angle

    def _platform_draft(
        self,
        platform: str,
        product_title: str,
        pillar: str,
        angle: str,
    ) -> PlatformPostDraftRead:
        caption = self.caption_generator.generate_for_platform(
            product_title=product_title,
            pillar=pillar,
            angle=angle,
            platform=self._caption_platform(platform),
        )

        return PlatformPostDraftRead(
            platform=platform,
            draft_caption=caption.caption,
            status="draft",
        )

    @staticmethod
    def _caption_platform(platform: str) -> CaptionPlatform:
        platform_map: dict[str, CaptionPlatform] = {
            "X": "x",
            "Facebook": "facebook",
            "Instagram": "instagram",
            "Pinterest": "pinterest",
        }
        return platform_map[platform]
