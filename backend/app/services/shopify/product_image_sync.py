from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import ProductImage
from app.services.shopify.types import ShopifyImage


class ProductImageSyncService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sync_images(self, product_id: int, images: list[ShopifyImage]) -> int:
        synced_count = 0

        for image in images:
            result = await self.session.exec(
                select(ProductImage).where(
                    ProductImage.shopify_image_id == image.shopify_image_id,
                ),
            )
            product_image = result.one_or_none()

            if product_image is None:
                product_image = ProductImage(
                    product_id=product_id,
                    shopify_image_id=image.shopify_image_id,
                    url=image.url,
                    alt_text=image.alt_text,
                    position=image.position,
                    width=image.width,
                    height=image.height,
                )
                self.session.add(product_image)
            else:
                product_image.product_id = product_id
                product_image.url = image.url
                product_image.alt_text = image.alt_text
                product_image.position = image.position
                product_image.width = image.width
                product_image.height = image.height

            synced_count += 1

        return synced_count

