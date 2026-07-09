from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ShopifyImage:
    shopify_image_id: str
    url: str
    alt_text: str | None
    width: int | None
    height: int | None
    position: int


@dataclass(frozen=True, slots=True)
class ShopifyProduct:
    shopify_product_id: str
    handle: str
    title: str
    vendor: str | None
    product_type: str | None
    status: str
    description: str | None
    tags: list[str]
    price: str | None
    currency_code: str | None
    total_inventory: int | None
    available_for_sale: bool
    images: list[ShopifyImage]

