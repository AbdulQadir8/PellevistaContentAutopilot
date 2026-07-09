from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app
from app.schemas import QualityCheckRequest, RecentCaptionRead
from app.services.quality import QualityCheckService


@pytest.fixture
def square_image_path(tmp_path) -> str:
    path = tmp_path / "asset.jpg"
    image = Image.new("RGB", (1200, 1200), color=(40, 50, 60))
    image.save(path, format="JPEG")
    return str(path)


def test_quality_checks_approve_candidate_but_require_manual_approval(
    square_image_path: str,
) -> None:
    result = QualityCheckService().evaluate(
        QualityCheckRequest(
            asset_file_path=square_image_path,
            asset_type="image",
            expected_aspect_ratio="1:1",
            minimum_width=1080,
            minimum_height=1080,
            caption="Black Oxford Red Sole Shoes make the full outfit intentional.",
            product_url="https://pellevista.example/products/black-oxford",
            check_date=date(2026, 7, 9),
        ),
    )

    assert result.score == 100
    assert result.status == "approved_candidate"
    assert result.manual_approval_required is True
    assert all(check.status == "pass" for check in result.checks)


def test_quality_checks_mark_needs_review_for_resolution_and_duplicate_caption(
    square_image_path: str,
) -> None:
    result = QualityCheckService().evaluate(
        QualityCheckRequest(
            asset_file_path=square_image_path,
            asset_type="image",
            expected_aspect_ratio="1:1",
            minimum_width=1600,
            minimum_height=1600,
            caption="A formal outfit is not complete until the shoes look intentional.",
            product_url="https://pellevista.example/products/black-oxford",
            check_date=date(2026, 7, 9),
            recent_captions=[
                RecentCaptionRead(
                    caption=(
                        "A formal outfit is not complete until the shoes look "
                        "intentional."
                    ),
                    posted_date=date(2026, 7, 6),
                ),
            ],
        ),
    )

    assert result.score == 70
    assert result.status == "needs_review"
    assert {
        check.name for check in result.checks if check.status == "fail"
    } == {"correct_minimum_resolution", "no_duplicate_caption_last_7_days"}


def test_quality_checks_reject_bad_assets_and_fake_discount(tmp_path) -> None:
    missing_path = tmp_path / "missing.jpg"
    result = QualityCheckService().evaluate(
        QualityCheckRequest(
            asset_file_path=str(missing_path),
            asset_type="image",
            expected_aspect_ratio="9:16",
            caption="Get 20% off today.",
            product_url=None,
            discount_active=False,
            check_date=date(2026, 7, 9),
            recent_captions=[],
        ),
    )

    assert result.score == 0
    assert result.status == "rejected"


def test_quality_checks_reject_fake_discount_claim(square_image_path: str) -> None:
    result = QualityCheckService().evaluate(
        QualityCheckRequest(
            asset_file_path=square_image_path,
            asset_type="image",
            expected_aspect_ratio="1:1",
            caption="Get 20% off Black Oxford Red Sole Shoes today.",
            product_url="https://pellevista.example/products/black-oxford",
            discount_active=False,
            check_date=date(2026, 7, 9),
        ),
    )

    assert result.score == 75
    assert result.status == "needs_review"
    assert any(
        check.name == "no_fake_discount_unless_active" and check.status == "fail"
        for check in result.checks
    )


@pytest.mark.asyncio
async def test_quality_check_endpoint(square_image_path: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/quality/check",
            json={
                "asset_file_path": square_image_path,
                "asset_type": "image",
                "expected_aspect_ratio": "1:1",
                "minimum_width": 1080,
                "minimum_height": 1080,
                "caption": "Black Oxford Red Sole Shoes make the outfit intentional.",
                "product_url": "https://pellevista.example/products/black-oxford",
                "discount_active": False,
                "check_date": "2026-07-09",
                "recent_captions": [],
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "approved_candidate"
    assert response.json()["manual_approval_required"] is True
