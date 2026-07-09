from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.content_strategy.product_selection import (
    ProductSelectionService,
    SelectionCandidate,
)


def test_product_selection_scores_exact_rules() -> None:
    service = ProductSelectionService()
    candidate = SelectionCandidate(
        product_title="Black Oxford Red Sole Shoes",
        tags=["oxford", "red-sole"],
        inventory_quantity=18,
        has_usable_image=True,
        available_for_sale=True,
        last_posted_date=None,
    )

    scored = service._score_candidate(candidate, date(2026, 7, 9))

    assert scored.score == 60


def test_product_selection_penalizes_recent_posts_and_out_of_stock() -> None:
    service = ProductSelectionService()
    candidate = SelectionCandidate(
        product_title="Black Loafers Red Sole",
        tags=["loafers", "red-sole"],
        inventory_quantity=0,
        has_usable_image=True,
        available_for_sale=False,
        last_posted_date=date(2026, 7, 5),
    )

    scored = service._score_candidate(candidate, date(2026, 7, 9))

    assert scored.score == -100


@pytest.mark.asyncio
async def test_daily_content_plan_uses_top_two_products() -> None:
    service = ProductSelectionService()

    ideas = await service.select_for_daily_content(
        plan_date=date(2026, 7, 9),
        number_of_ideas=2,
    )

    assert [idea.product_title for idea in ideas] == [
        "Black Oxford Red Sole Shoes",
        "Brown Monk Strap Leather Shoes",
    ]


@pytest.mark.asyncio
async def test_daily_content_plan_endpoint() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/content-plans/daily",
            json={"date": "2026-07-09", "number_of_ideas": 2},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-07-09"
    assert payload["total_drafts"] == 8
    assert len(payload["content_ideas"]) == 2
    assert payload["content_ideas"][0]["platform_post_drafts"] == [
        {
            "platform": "X",
            "draft_caption": (
                "Most men spend hundreds on a suit, then ruin the look with cheap "
                "shoes.\n\nPelleVista handcrafted leather shoes are made to finish "
                "the outfit properly."
            ),
            "status": "draft",
        },
        {
            "platform": "Facebook",
            "draft_caption": (
                "Most men spend hundreds on a suit, then ruin the look with cheap "
                "shoes.\n\nBlack Oxford Red Sole Shoes is built to bring polish, "
                "structure, and presence to formal outfits without changing the man "
                "wearing them.\n\nExplore PelleVista handcrafted leather shoes."
            ),
            "status": "draft",
        },
        {
            "platform": "Instagram",
            "draft_caption": (
                "A sharp suit deserves shoes that match the effort.\n\nHandcrafted "
                "PelleVista leather shoes bring polish, structure, and presence to "
                "formal outfits.\n\n#MensStyle #LeatherShoes #OxfordShoes"
            ),
            "status": "draft",
        },
        {
            "platform": "Pinterest",
            "draft_caption": (
                "Title: Handcrafted Men's Black Oxford Shoes\n\nDescription:\n"
                "Premium handcrafted men's leather oxford shoes for formal outfits, "
                "weddings, office wear, and luxury style."
            ),
            "status": "draft",
        },
    ]
    assert {
        "product_title": payload["content_ideas"][0]["product_title"],
        "pillar": payload["content_ideas"][0]["pillar"],
        "angle": payload["content_ideas"][0]["angle"],
    } == {
        "product_title": "Black Oxford Red Sole Shoes",
        "pillar": "Pain-point hook",
        "angle": (
            "Most men spend hundreds on a suit, then ruin the look with cheap shoes."
        ),
    }
