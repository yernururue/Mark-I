from fastapi import APIRouter, Depends, Query
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.dependencies import get_db, get_current_user_id
from app.models.dashboard import DashboardResponse, DashboardStats
from app.services.skill_service import SkillService
from app.services.observation_service import ObservationService

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    observationLimit: int = Query(10, ge=1, le=50),
    decisionLimit: int = Query(5, ge=1, le=20),
    uid: str = Depends(get_current_user_id),
    db: FirestoreClient = Depends(get_db)
):
    """
    Get aggregated dashboard data.
    """
    skill_service = SkillService(db)
    obs_service = ObservationService(db)

    skills = skill_service.get_skills(uid)
    observations = obs_service.get_recent_observations(uid, limit=observationLimit)
    
    # Decisions not implemented in this phase, mock for now
    decisions = []
    
    # Calculate stats
    total_obs_query = obs_service._get_collection(uid).count()
    total_obs = total_obs_query.get()[0][0].value if hasattr(total_obs_query, "get") else 0
    
    stats = DashboardStats(
        totalObservations=total_obs,
        totalDecisions=0,
        activeSkills=len(skills),
        overallTrend="stable" # mock
    )

    return DashboardResponse(
        skills=skills,
        recentObservations=observations,
        recentDecisions=decisions,
        stats=stats
    )
