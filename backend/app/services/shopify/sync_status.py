from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

SyncState = Literal["idle", "running", "completed", "failed"]


@dataclass(slots=True)
class ShopifySyncStatus:
    status: SyncState = "idle"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    products_synced: int = 0
    images_synced: int = 0
    message: str = "No sync has run yet."

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "products_synced": self.products_synced,
            "images_synced": self.images_synced,
            "message": self.message,
        }


sync_status = ShopifySyncStatus()


def mark_running() -> None:
    sync_status.status = "running"
    sync_status.started_at = datetime.now(UTC)
    sync_status.completed_at = None
    sync_status.products_synced = 0
    sync_status.images_synced = 0
    sync_status.message = "Shopify sync is running."


def mark_completed(products_synced: int, images_synced: int) -> None:
    sync_status.status = "completed"
    sync_status.completed_at = datetime.now(UTC)
    sync_status.products_synced = products_synced
    sync_status.images_synced = images_synced
    sync_status.message = "Shopify sync completed."


def mark_failed(message: str) -> None:
    sync_status.status = "failed"
    sync_status.completed_at = datetime.now(UTC)
    sync_status.message = message

