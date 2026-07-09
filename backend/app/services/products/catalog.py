from datetime import datetime

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Product, ProductImage
from app.schemas import ProductImageRead, ProductRead


class ProductCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_products(self) -> list[ProductRead]:
        result = await self.session.exec(
            select(Product).order_by(
                col(Product.priority_score).desc(),
                col(Product.title),
            ),
        )
        products = result.all()
        return [await self._to_product_read(product) for product in products]

    async def get_product(self, product_id: int) -> ProductRead | None:
        product = await self.session.get(Product, product_id)
        if product is None:
            return None

        return await self._to_product_read(product)

    async def list_product_images(
        self,
        product_id: int | None = None,
    ) -> list[ProductImageRead]:
        statement = select(ProductImage).order_by(
            col(ProductImage.product_id),
            col(ProductImage.position),
        )
        if product_id is not None:
            statement = statement.where(ProductImage.product_id == product_id)

        result = await self.session.exec(statement)
        return [
            ProductImageRead.model_validate(image)
            for image in result.all()
        ]

    async def _to_product_read(self, product: Product) -> ProductRead:
        image = await self._primary_image(product.id)
        return ProductRead(
            id=product.id or 0,
            brand_id=product.brand_id,
            shopify_product_id=product.shopify_product_id,
            handle=product.handle,
            title=product.title,
            vendor=product.vendor,
            product_type=product.product_type,
            status=product.status,
            description=product.description,
            tags=self._parse_tags(product.tags),
            price=product.price,
            currency_code=product.currency_code,
            image_url=image.url if image else None,
            total_inventory=product.total_inventory,
            available_for_sale=product.available_for_sale,
            eligible_for_content=product.eligible_for_content,
            last_posted_date=self._date_string(product.last_posted_at),
            priority_score=product.priority_score,
            last_synced_at=product.last_synced_at,
        )

    async def _primary_image(self, product_id: int | None) -> ProductImage | None:
        if product_id is None:
            return None

        result = await self.session.exec(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(col(ProductImage.position))
            .limit(1),
        )
        return result.one_or_none()

    @staticmethod
    def _parse_tags(tags: str | None) -> list[str]:
        if not tags:
            return []

        return [tag.strip() for tag in tags.split(",") if tag.strip()]

    @staticmethod
    def _date_string(value: datetime | None) -> str | None:
        if value is None:
            return None

        return value.date().isoformat()
