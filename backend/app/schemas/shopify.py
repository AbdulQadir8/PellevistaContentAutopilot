from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SyncState = Literal["idle", "running", "completed", "failed"]


class ShopifySyncStatusRead(BaseModel):
    status: SyncState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    products_synced: int
    images_synced: int
    message: str
