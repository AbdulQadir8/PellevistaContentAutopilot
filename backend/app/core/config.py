from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Pellevista Content Autopilot API"
    openai_api_key: str = ""
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pellevista_content"
    frontend_origin: str = "http://localhost:5173"
    shopify_shop_domain: str = ""
    shopify_admin_access_token: str = ""
    shopify_api_version: str = "2025-10"
    recent_post_window_days: int = 14
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    higgsfield_application: str = "pellevista-product-creative"
    asset_bucket_name: str = ""
    asset_bucket_region: str = "auto"
    asset_bucket_endpoint_url: str = ""
    asset_public_base_url: str = ""
    x_api_base_url: str = "https://api.x.com"
    x_user_access_token: str = ""
    x_public_post_base_url: str = "https://x.com/i/web/status"
    pinterest_api_base_url: str = "https://api.pinterest.com/v5"
    pinterest_access_token: str = ""
    pinterest_board_id: str = ""
    pinterest_board_name: str = ""
    pinterest_public_pin_base_url: str = "https://www.pinterest.com/pin"
    pellevista_store_base_url: str = ""


settings = Settings()
