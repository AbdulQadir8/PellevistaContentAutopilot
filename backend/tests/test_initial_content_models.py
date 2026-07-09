from sqlmodel import SQLModel

from app.models import Brand, ContentIdea, PlatformPost, Product, ProductImage


def test_initial_content_tables_are_registered() -> None:
    assert {
        "brands",
        "products",
        "product_images",
        "content_ideas",
        "platform_posts",
    }.issubset(SQLModel.metadata.tables)


def test_can_build_initial_content_flow() -> None:
    brand = Brand(name="Pellevista", slug="pellevista")
    product = Product(
        brand_id=1,
        shopify_product_id="gid://shopify/Product/123",
        handle="hydrating-serum",
        title="Hydrating Serum",
        vendor="Pellevista",
        product_type="Serum",
    )
    image = ProductImage(
        product_id=1,
        shopify_image_id="gid://shopify/ProductImage/456",
        url="https://cdn.example.com/hydrating-serum.jpg",
        alt_text="Hydrating serum bottle",
        position=1,
    )
    idea = ContentIdea(
        brand_id=1,
        product_id=1,
        title="Hydration routine spotlight",
        angle="Show how the serum fits into a morning skincare routine.",
    )
    post = PlatformPost(
        content_idea_id=1,
        product_id=1,
        platform="instagram",
        draft_caption="A simple hydration-first routine for busy mornings.",
    )

    assert brand.slug == "pellevista"
    assert product.shopify_product_id == "gid://shopify/Product/123"
    assert image.url.endswith("hydrating-serum.jpg")
    assert idea.status == "draft"
    assert post.status == "draft"
