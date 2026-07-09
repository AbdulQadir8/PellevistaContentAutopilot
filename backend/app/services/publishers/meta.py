from typing import Final

META_DEFERRED_PLATFORMS: Final[set[str]] = {"instagram", "facebook"}
META_DEFERRED_MESSAGE: Final[str] = (
    "Meta publishing is deferred until OAuth and token storage are ready."
)


class MetaPublishingDeferredError(RuntimeError):
    pass


class MetaOAuthService:
    def authorization_url(self) -> str:
        raise MetaPublishingDeferredError(
            META_DEFERRED_MESSAGE,
        )

    async def exchange_code(self, code: str) -> None:
        raise MetaPublishingDeferredError(META_DEFERRED_MESSAGE)


class InstagramPublisher:
    async def publish_post(self, post_id: int) -> None:
        raise MetaPublishingDeferredError(META_DEFERRED_MESSAGE)


class FacebookPublisher:
    async def publish_post(self, post_id: int) -> None:
        raise MetaPublishingDeferredError(META_DEFERRED_MESSAGE)
