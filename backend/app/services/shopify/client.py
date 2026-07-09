from typing import Any

import httpx

from app.core.config import settings
from app.services.shopify.types import ShopifyImage, ShopifyProduct


class ShopifyConfigError(RuntimeError):
    pass


class ShopifyAPIError(RuntimeError):
    pass


class ShopifyClient:
    def __init__(
        self,
        shop_domain: str = settings.shopify_shop_domain,
        access_token: str = settings.shopify_admin_access_token,
        api_version: str = settings.shopify_api_version,
    ) -> None:
        self.shop_domain = shop_domain.strip()
        self.access_token = access_token.strip()
        self.api_version = api_version.strip()

        if not self.shop_domain or not self.access_token:
            raise ShopifyConfigError(
                "SHOPIFY_SHOP_DOMAIN and SHOPIFY_ADMIN_ACCESS_TOKEN are required.",
            )

    async def fetch_products(self, page_size: int = 50) -> list[ShopifyProduct]:
        products: list[ShopifyProduct] = []
        cursor: str | None = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                payload = await self._execute_products_query(
                    client=client,
                    page_size=page_size,
                    cursor=cursor,
                )
                product_connection = payload["data"]["products"]
                products.extend(
                    self._parse_product(node)
                    for node in product_connection.get("nodes", [])
                )

                page_info = product_connection["pageInfo"]
                if not page_info["hasNextPage"]:
                    break

                cursor = page_info["endCursor"]

        return products

    async def _execute_products_query(
        self,
        client: httpx.AsyncClient,
        page_size: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        response = await client.post(
            self._graphql_url,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.access_token,
            },
            json={
                "query": PRODUCTS_QUERY,
                "variables": {"first": page_size, "after": cursor},
            },
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("errors"):
            raise ShopifyAPIError(str(payload["errors"]))

        return payload

    @property
    def _graphql_url(self) -> str:
        domain = self.shop_domain.removeprefix("https://").removeprefix("http://")
        return f"https://{domain}/admin/api/{self.api_version}/graphql.json"

    def _parse_product(self, node: dict[str, Any]) -> ShopifyProduct:
        variant = self._first_node(node.get("variants", {}))
        images = [
            ShopifyImage(
                shopify_image_id=image["id"],
                url=image["url"],
                alt_text=image.get("altText"),
                width=image.get("width"),
                height=image.get("height"),
                position=index + 1,
            )
            for index, image in enumerate(node.get("images", {}).get("nodes", []))
        ]

        return ShopifyProduct(
            shopify_product_id=node["id"],
            handle=node["handle"],
            title=node["title"],
            vendor=node.get("vendor"),
            product_type=node.get("productType"),
            status=str(node.get("status", "")).lower(),
            description=node.get("descriptionHtml") or None,
            tags=list(node.get("tags", [])),
            price=self._variant_price(variant),
            currency_code=self._variant_currency_code(variant),
            total_inventory=node.get("totalInventory"),
            available_for_sale=bool(variant and variant.get("availableForSale")),
            images=images,
        )

    @staticmethod
    def _first_node(connection: dict[str, Any]) -> dict[str, Any] | None:
        nodes = connection.get("nodes", [])
        if not nodes:
            return None

        return nodes[0]

    @staticmethod
    def _variant_price(variant: dict[str, Any] | None) -> str | None:
        if not variant:
            return None

        price = variant.get("price")
        if isinstance(price, dict):
            return price.get("amount")

        if isinstance(price, str):
            return price

        return None

    @staticmethod
    def _variant_currency_code(variant: dict[str, Any] | None) -> str | None:
        if not variant:
            return None

        price = variant.get("price")
        if isinstance(price, dict):
            return price.get("currencyCode")

        return None


PRODUCTS_QUERY = """
query PellevistaProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      handle
      title
      vendor
      productType
      status
      descriptionHtml
      tags
      totalInventory
      images(first: 20) {
        nodes {
          id
          url
          altText
          width
          height
        }
      }
      variants(first: 1) {
        nodes {
          availableForSale
          price {
            amount
            currencyCode
          }
        }
      }
    }
  }
}
"""

