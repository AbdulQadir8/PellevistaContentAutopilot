from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.schemas import DailyContentPlanRead, DailyContentPlanRequest
from app.services.content_strategy import ContentStrategyService

router = APIRouter(prefix="/content-plans", tags=["content-plans"])


@router.post("/daily", response_model=DailyContentPlanRead)
async def create_daily_content_plan(
    payload: DailyContentPlanRequest,
    session: AsyncSession = Depends(get_session),
) -> DailyContentPlanRead:
    return await ContentStrategyService(session).create_daily_plan(
        plan_date=payload.date,
        number_of_ideas=payload.number_of_ideas,
    )
