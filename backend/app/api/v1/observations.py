from typing import Literal
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user_id, get_observation_service
from app.models.observation import ObservationsResponse
from app.services.observation_service import ObservationService

router = APIRouter(tags=["Observations"])

@router.get("/observations", response_model=ObservationsResponse)
async def get_observations(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    source: Literal["github", "opportunity", "chat"] | None = None,
    concept: str | None = None,
    uid: str = Depends(get_current_user_id),
    observation_service: ObservationService = Depends(get_observation_service),
):
    """
    Get observations with pagination and optional filters.
    """
    return observation_service.get_observations(
        uid=uid,
        limit=limit,
        cursor=cursor,
        source=source,
        concept=concept,
    )
