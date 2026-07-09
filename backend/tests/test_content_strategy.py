from datetime import date

import pytest

from app.services.content_strategy import CONTENT_PILLARS, ContentStrategyService


def test_fixed_content_pillars_are_defined() -> None:
    assert CONTENT_PILLARS == [
        "Pain-point hook",
        "Product beauty",
        "Craftsmanship",
        "Style education",
        "Red-sole positioning",
        "Offer",
        "Social proof",
        "Occasion",
    ]


@pytest.mark.asyncio
async def test_content_strategy_creates_two_ideas_and_eight_drafts() -> None:
    plan = await ContentStrategyService().create_daily_plan(
        plan_date=date(2026, 7, 9),
        number_of_ideas=2,
    )

    assert len(plan.content_ideas) == 2
    assert plan.total_drafts == 8
    assert all(
        len(content_idea.platform_post_drafts) == 4
        for content_idea in plan.content_ideas
    )
    assert [
        draft.platform
        for draft in plan.content_ideas[0].platform_post_drafts
    ] == ["X", "Facebook", "Instagram", "Pinterest"]

