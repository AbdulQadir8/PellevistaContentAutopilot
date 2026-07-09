from uuid import UUID

from pydantic import BaseModel

from app.schemas.prompt import PlatformName


class GenerationRequest(BaseModel):
    platform: PlatformName = "instagram"
    aspect_ratio: str | None = None
    creative_style: str = "premium editorial menswear product advertisement"


class GenerationAcceptedRead(BaseModel):
    job_id: UUID
    status: str
