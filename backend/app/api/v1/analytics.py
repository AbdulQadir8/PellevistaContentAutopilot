from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.schemas import AnalyticsDashboardRead
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboardRead)
async def get_analytics_dashboard(
    session: AsyncSession = Depends(get_session),
) -> AnalyticsDashboardRead:
    return await AnalyticsService(session).dashboard()
