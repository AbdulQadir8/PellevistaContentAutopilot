from pydantic import BaseModel, ConfigDict


class ProductImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    shopify_image_id: str | None = None
    url: str
    alt_text: str | None = None
    position: int
    width: int | None = None
    height: int | None = None
