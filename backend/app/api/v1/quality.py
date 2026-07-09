from fastapi import APIRouter

from app.schemas import QualityCheckRequest, QualityCheckResultRead
from app.services.quality import QualityCheckService

router = APIRouter(prefix="/quality", tags=["quality"])


@router.post("/check", response_model=QualityCheckResultRead)
async def check_quality(payload: QualityCheckRequest) -> QualityCheckResultRead:
    return QualityCheckService().evaluate(payload)

