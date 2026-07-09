from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    shopify_product_id: str
    handle: str
    title: str
    vendor: str | None = None
    product_type: str | None = None
    status: str
    description: str | None = None
    tags: list[str]
    price: str | None = None
    currency_code: str | None = None
    image_url: str | None = None
    total_inventory: int | None = None
    available_for_sale: bool = False
    eligible_for_content: bool = False
    last_posted_date: str | None = None
    priority_score: int = 0
    last_synced_at: datetime | None = None
