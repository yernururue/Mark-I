from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user_id, get_dashboard_service
from app.models.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    observationLimit: int = Query(10, ge=1, le=50),
    decisionLimit: int = Query(5, ge=1, le=20),
    uid: str = Depends(get_current_user_id),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get aggregated dashboard data.
    """
    return dashboard_service.get_dashboard(uid, observationLimit, decisionLimit)
