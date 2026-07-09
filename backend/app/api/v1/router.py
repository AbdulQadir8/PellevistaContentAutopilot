from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    assets,
    brands,
    content_ideas,
    content_plans,
    health,
    platform_posts,
    product_images,
    products,
    quality,
    shopify,
)

api_router = APIRouter()
api_router.include_router(analytics.router)
api_router.include_router(health.router)
api_router.include_router(brands.router)
api_router.include_router(content_ideas.router)
api_router.include_router(content_plans.router)
api_router.include_router(assets.router)
api_router.include_router(platform_posts.router)
api_router.include_router(products.router)
api_router.include_router(product_images.router)
api_router.include_router(shopify.router)
api_router.include_router(quality.router)
