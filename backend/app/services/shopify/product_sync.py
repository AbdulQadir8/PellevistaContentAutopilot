from datetime import UTC, datetime, timedelta

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models import Brand, PlatformPost, Product
from app.services.shopify.client import ShopifyClient
from app.services.shopify.product_image_sync import ProductImageSyncService
from app.services.shopify.types import ShopifyProduct


class ProductSyncService:
    def __init__(
        self,
        session: AsyncSession,
        client: ShopifyClient | None = None,
    ) -> None:
        self.session = session
        self.client = client or ShopifyClient()
        self.image_sync_service = ProductImageSyncService(session)

    async def sync(self) -> tuple[int, int]:
        brand = await self._ensure_pellevista_brand()
        products = await self.client.fetch_products()

        products_synced = 0
        images_synced = 0
        for shopify_product in products:
            product = await self._upsert_product(brand.id, shopify_product)
            await self.session.flush()

            if product.id is None:
                continue

            image_count = await self.image_sync_service.sync_images(
                product_id=product.id,
                images=shopify_product.images,
            )
            product.has_image = image_count > 0
            product.last_posted_at = await self._last_posted_at(product.id)
            product.eligible_for_content = self._is_eligible(product)
            product.priority_score = self._priority_score(product)

            products_synced += 1
            images_synced += image_count

        await self.session.commit()
        return products_synced, images_synced

    async def _ensure_pellevista_brand(self) -> Brand:
        result = await self.session.exec(select(Brand).where(Brand.slug == "pellevista"))
        brand = result.one_or_none()

        if brand is None:
            brand = Brand(
                name="PelleVista",
                slug="pellevista",
                shopify_domain=settings.shopify_shop_domain or None,
            )
            self.session.add(brand)
            await self.session.flush()
        elif settings.shopify_shop_domain:
            brand.shopify_domain = settings.shopify_shop_domain
            brand.updated_at = datetime.now(UTC)

        return brand

    async def _upsert_product(
        self,
        brand_id: int | None,
        shopify_product: ShopifyProduct,
    ) -> Product:
        if brand_id is None:
            raise RuntimeError("Brand must be flushed before syncing products.")

        result = await self.session.exec(
            select(Product).where(
                Product.shopify_product_id == shopify_product.shopify_product_id,
            ),
        )
        product = result.one_or_none()
        now = datetime.now(UTC)
        tags = ",".join(shopify_product.tags)

        if product is None:
            product = Product(
                brand_id=brand_id,
                shopify_product_id=shopify_product.shopify_product_id,
                handle=shopify_product.handle,
                title=shopify_product.title,
            )
            self.session.add(product)

        product.brand_id = brand_id
        product.handle = shopify_product.handle
        product.title = shopify_product.title
        product.vendor = shopify_product.vendor
        product.product_type = shopify_product.product_type
        product.status = shopify_product.status
        product.description = shopify_product.description
        product.tags = tags
        product.price = shopify_product.price
        product.currency_code = shopify_product.currency_code
        product.total_inventory = shopify_product.total_inventory
        product.available_for_sale = shopify_product.available_for_sale
        product.last_synced_at = now
        product.updated_at = now

        return product

    async def _last_posted_at(self, product_id: int) -> datetime | None:
        result = await self.session.exec(
            select(PlatformPost)
            .where(
                PlatformPost.product_id == product_id,
                col(PlatformPost.status).in_(["posted", "published"]),
            )
            .order_by(col(PlatformPost.scheduled_for).desc())
            .limit(1),
        )
        post = result.one_or_none()
        if post is None:
            return None

        return post.scheduled_for or post.updated_at

    def _is_eligible(self, product: Product) -> bool:
        return all(
            [
                product.status.lower() == "active",
                product.has_image,
                bool(product.price),
                product.available_for_sale,
                not self._was_recently_posted(product.last_posted_at),
            ],
        )

    def _priority_score(self, product: Product) -> int:
        score = 0
        if product.status.lower() == "active":
            score += 20
        if product.has_image:
            score += 20
        if product.price:
            score += 15
        if product.available_for_sale:
            score += 15
        if not self._was_recently_posted(product.last_posted_at):
            score += 20
        if product.tags:
            score += min(10, len(product.tags.split(",")) * 2)

        return min(score, 100)

    def _was_recently_posted(self, last_posted_at: datetime | None) -> bool:
        if last_posted_at is None:
            return False

        cutoff = datetime.now(UTC) - timedelta(days=settings.recent_post_window_days)
        return last_posted_at >= cutoff
