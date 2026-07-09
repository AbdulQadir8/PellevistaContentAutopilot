from app.schemas import (
    PromptBuilderInput,
    PromptProductImageInput,
    PromptProductInput,
)
from app.services.prompt_builder import PLATFORM_FORMATS, PromptBuilderService


def test_platform_formats_match_generation_defaults() -> None:
    assert PLATFORM_FORMATS == {
        "instagram": {"aspect_ratio": "9:16", "asset_type": "video"},
        "pinterest": {"aspect_ratio": "2:3", "asset_type": "image"},
        "facebook": {"aspect_ratio": "4:5", "asset_type": "image"},
        "x": {"aspect_ratio": "16:9", "asset_type": "image"},
    }


def test_prompt_builder_creates_higgsfield_prompt_with_strict_product_fidelity() -> None:
    output = PromptBuilderService().build(
        PromptBuilderInput(
            product=PromptProductInput(
                title="Black Oxford Red Sole Shoes",
                product_type="Dress Shoes",
                tags=["oxford", "black", "red-sole", "formal"],
                price="$189",
            ),
            product_image=PromptProductImageInput(
                url="https://cdn.example.com/black-oxford-red-sole.jpg",
                alt_text="Black Oxford Red Sole Shoes side profile",
            ),
            content_pillar="Pain-point hook",
            angle=(
                "Most men spend hundreds on a suit, then ruin the look with cheap "
                "shoes."
            ),
            platform="instagram",
            creative_style="premium studio video",
        ),
    )

    assert "Product: Black Oxford Red Sole Shoes." in output.higgsfield_prompt
    assert "provided reference image as the strict source of truth" in (
        output.higgsfield_prompt
    )
    assert "Preserve the exact shoe identity" in output.higgsfield_prompt
    assert "red sole is a key brand detail" in output.higgsfield_prompt
    assert "Do not redesign, restyle, recolor, replace" in output.higgsfield_prompt
    assert output.generation_settings.aspect_ratio == "9:16"
    assert output.generation_settings.asset_type == "video"
    assert output.generation_settings.duration_seconds == 6
    assert output.generation_settings.reference_image_url == (
        "https://cdn.example.com/black-oxford-red-sole.jpg"
    )


def test_prompt_builder_negative_prompt_blocks_wrong_shoes() -> None:
    output = PromptBuilderService().build_from_parts(
        product=PromptProductInput(
            title="Brown Monk Strap Leather Shoes",
            product_type="Dress Shoes",
            tags=["monk-strap", "brown", "leather"],
        ),
        product_image=PromptProductImageInput(
            url="https://cdn.example.com/brown-monk-strap.jpg",
        ),
        content_pillar="Craftsmanship",
        angle="Call out the details that make the pair feel built, not just styled.",
        platform="pinterest",
    )

    assert "wrong shoe" in output.negative_prompt
    assert "different shoe" in output.negative_prompt
    assert "sneakers" in output.negative_prompt
    assert "boots" in output.negative_prompt
    assert "sandals" in output.negative_prompt
    assert "not Brown Monk Strap Leather Shoes" in output.negative_prompt


def test_prompt_builder_allows_aspect_ratio_override() -> None:
    output = PromptBuilderService().build_from_parts(
        product=PromptProductInput(
            title="Oxblood Wholecut Oxford Shoes",
            product_type="Dress Shoes",
            tags=["wholecut", "oxford", "oxblood"],
        ),
        product_image=PromptProductImageInput(
            url="https://cdn.example.com/oxblood-wholecut.jpg",
        ),
        content_pillar="Product beauty",
        angle="Lead with the silhouette and shine.",
        platform="facebook",
        aspect_ratio="1:1",
        creative_style="square studio image",
    )

    assert output.generation_settings.aspect_ratio == "1:1"
    assert output.generation_settings.asset_type == "image"
    assert output.generation_settings.duration_seconds is None
    assert "Aspect ratio: 1:1." in output.higgsfield_prompt

