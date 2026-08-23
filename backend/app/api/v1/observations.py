from typing import Optional
from fastapi import APIRouter, Depends, Query
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.dependencies import get_db, get_current_user_id
from app.models.observation import ObservationsResponse
from app.services.observation_service import ObservationService

router = APIRouter(tags=["Observations"])

@router.get("/observations", response_model=ObservationsResponse)
async def get_observations(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = None,
    source: Optional[str] = None,
    concept: Optional[str] = None,
    uid: str = Depends(get_current_user_id),
    db: FirestoreClient = Depends(get_db)
):
    """
    Get observations with pagination and optional filters.
    """
    # NOTE: Pagination cursor implementation is omitted for brevity MVP.
    # It just returns latest 'limit' observations.
    observation_service = ObservationService(db)
    items = observation_service.get_recent_observations(
        uid=uid,
        limit=limit,
        concept=concept
    )
    
    return ObservationsResponse(items=items, nextCursor=None)
