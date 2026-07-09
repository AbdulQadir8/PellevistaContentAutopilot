from app.schemas import CaptionGeneratorInput
from app.services.captions import STRICT_BRAND_RULES, CaptionGeneratorService


def test_x_caption_uses_pain_point_template() -> None:
    output = CaptionGeneratorService().generate(
        CaptionGeneratorInput(
            product_title="Black Oxford Red Sole Shoes",
            product_type="Dress Shoes",
            tags=["oxford", "black", "red-sole", "formal"],
            pillar="Pain-point hook",
            angle="Most men spend hundreds on a suit, then ruin the look with cheap shoes.",
            platform="x",
        ),
    )

    assert output.caption == (
        "Most men spend hundreds on a suit, then ruin the look with cheap shoes.\n\n"
        "PelleVista handcrafted leather shoes are made to finish the outfit properly."
    )


def test_instagram_caption_uses_brand_template_and_hashtags() -> None:
    output = CaptionGeneratorService().generate(
        CaptionGeneratorInput(
            product_title="Black Oxford Red Sole Shoes",
            product_type="Dress Shoes",
            tags=["oxford", "black", "red-sole", "formal"],
            pillar="Product beauty",
            angle="Lead with the silhouette, shine, and shape.",
            platform="instagram",
        ),
    )

    assert output.caption == (
        "A sharp suit deserves shoes that match the effort.\n\n"
        "Handcrafted PelleVista leather shoes bring polish, structure, and "
        "presence to formal outfits.\n\n"
        "#MensStyle #LeatherShoes #OxfordShoes"
    )


def test_pinterest_caption_returns_title_and_description() -> None:
    output = CaptionGeneratorService().generate(
        CaptionGeneratorInput(
            product_title="Black Oxford Red Sole Shoes",
            product_type="Dress Shoes",
            tags=["oxford", "black", "red-sole", "formal"],
            pillar="Product beauty",
            angle="Lead with the silhouette, shine, and shape.",
            platform="pinterest",
        ),
    )

    assert output.title == "Handcrafted Men's Black Oxford Shoes"
    assert output.description == (
        "Premium handcrafted men's leather oxford shoes for formal outfits, "
        "weddings, office wear, and luxury style."
    )
    assert output.caption == (
        "Title: Handcrafted Men's Black Oxford Shoes\n\n"
        "Description:\n"
        "Premium handcrafted men's leather oxford shoes for formal outfits, "
        "weddings, office wear, and luxury style."
    )


def test_caption_generator_exposes_strict_brand_rules() -> None:
    assert "Never invent discounts, sale claims, or scarcity." in STRICT_BRAND_RULES
    assert "Use PelleVista spelling exactly." in STRICT_BRAND_RULES
