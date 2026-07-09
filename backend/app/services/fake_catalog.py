import re
from dataclasses import dataclass, field

from app.schemas import BrandCreate, BrandRead, ProductImageRead, ProductRead


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "brand"


@dataclass(slots=True)
class FakeCatalogStore:
    brands: list[BrandRead] = field(
        default_factory=lambda: [
            BrandRead(
                id=1,
                name="PelleVista",
                slug="pellevista",
                shopify_domain="pellevista.myshopify.com",
            )
        ]
    )
    products: list[ProductRead] = field(
        default_factory=lambda: [
            ProductRead(
                id=1,
                brand_id=1,
                shopify_product_id="gid://shopify/Product/1001",
                handle="black-oxford-red-sole-shoes",
                title="Black Oxford Red Sole Shoes",
                vendor="PelleVista",
                product_type="Dress Shoes",
                status="active",
                description="Polished black Oxford shoes with PelleVista red soles.",
                tags=["oxford", "black", "red-sole", "formal"],
                price="$189",
                currency_code="USD",
                image_url="https://placehold.co/160x160/png?text=Black%20Oxford%0ARed%20Sole",
                total_inventory=18,
                available_for_sale=True,
                eligible_for_content=True,
                last_posted_date="2026-07-01",
                priority_score=94,
            ),
            ProductRead(
                id=2,
                brand_id=1,
                shopify_product_id="gid://shopify/Product/1002",
                handle="brown-monk-strap-leather-shoes",
                title="Brown Monk Strap Leather Shoes",
                vendor="PelleVista",
                product_type="Dress Shoes",
                status="active",
                description="Brown leather monk strap shoes for smart styling.",
                tags=["monk-strap", "brown", "leather", "formal"],
                price="$205",
                currency_code="USD",
                image_url="https://placehold.co/160x160/png?text=Brown%20Monk%0AStrap",
                total_inventory=12,
                available_for_sale=True,
                eligible_for_content=True,
                last_posted_date=None,
                priority_score=88,
            ),
            ProductRead(
                id=3,
                brand_id=1,
                shopify_product_id="gid://shopify/Product/1003",
                handle="oxblood-wholecut-oxford-shoes",
                title="Oxblood Wholecut Oxford Shoes",
                vendor="PelleVista",
                product_type="Dress Shoes",
                status="active",
                description="Oxblood wholecut Oxford shoes with a clean silhouette.",
                tags=["wholecut", "oxford", "oxblood", "formal"],
                price="$229",
                currency_code="USD",
                image_url="https://placehold.co/160x160/png?text=Oxblood%0AWholecut",
                total_inventory=7,
                available_for_sale=True,
                eligible_for_content=True,
                last_posted_date="2026-06-24",
                priority_score=81,
            ),
            ProductRead(
                id=4,
                brand_id=1,
                shopify_product_id="gid://shopify/Product/1004",
                handle="black-loafers-red-sole",
                title="Black Loafers Red Sole",
                vendor="PelleVista",
                product_type="Loafers",
                status="active",
                description="Black loafers finished with signature red soles.",
                tags=["loafers", "black", "red-sole", "smart-casual"],
                price="$174",
                currency_code="USD",
                image_url="https://placehold.co/160x160/png?text=Black%20Loafers%0ARed%20Sole",
                total_inventory=0,
                available_for_sale=False,
                eligible_for_content=False,
                last_posted_date="2026-06-17",
                priority_score=62,
            ),
        ]
    )
    product_images: list[ProductImageRead] = field(
        default_factory=lambda: [
            ProductImageRead(
                id=1,
                product_id=1,
                shopify_image_id="gid://shopify/ProductImage/2001",
                url="https://cdn.pellevista.example/products/black-oxford-red-sole.jpg",
                alt_text="Black Oxford Red Sole Shoes",
                position=1,
                width=1200,
                height=1200,
            ),
            ProductImageRead(
                id=2,
                product_id=2,
                shopify_image_id="gid://shopify/ProductImage/2002",
                url="https://cdn.pellevista.example/products/brown-monk-strap.jpg",
                alt_text="Brown Monk Strap Leather Shoes",
                position=1,
                width=1200,
                height=1200,
            ),
            ProductImageRead(
                id=3,
                product_id=3,
                shopify_image_id="gid://shopify/ProductImage/2003",
                url="https://cdn.pellevista.example/products/oxblood-wholecut-oxford.jpg",
                alt_text="Oxblood Wholecut Oxford Shoes",
                position=1,
                width=1200,
                height=1200,
            ),
            ProductImageRead(
                id=4,
                product_id=4,
                shopify_image_id="gid://shopify/ProductImage/2004",
                url="https://cdn.pellevista.example/products/black-loafers-red-sole.jpg",
                alt_text="Black Loafers Red Sole",
                position=1,
                width=1200,
                height=1200,
            ),
        ]
    )

    def create_brand(self, payload: BrandCreate) -> BrandRead:
        brand = BrandRead(
            id=self._next_brand_id(),
            name=payload.name,
            slug=payload.slug or _slugify(payload.name),
            shopify_domain=payload.shopify_domain,
        )
        self.brands.append(brand)
        return brand

    def list_brands(self) -> list[BrandRead]:
        return self.brands

    def list_products(self) -> list[ProductRead]:
        return self.products

    def get_product(self, product_id: int) -> ProductRead | None:
        return next(
            (product for product in self.products if product.id == product_id),
            None,
        )

    def list_product_images(self, product_id: int | None = None) -> list[ProductImageRead]:
        if product_id is None:
            return self.product_images

        return [
            image for image in self.product_images if image.product_id == product_id
        ]

    def _next_brand_id(self) -> int:
        return max((brand.id for brand in self.brands), default=0) + 1


fake_catalog_store = FakeCatalogStore()
