import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.dependencies import get_opportunity_service
from app.services.opportunity_service import OpportunityService

router = APIRouter(tags=["Triggers"])

@router.post("/trigger/opportunities", include_in_schema=False)
async def trigger_opportunities(
    x_scheduler_secret: Annotated[str | None, Header(alias="X-Scheduler-Secret")] = None,
    settings: Settings = Depends(get_settings),
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
):
    """Start collection only for a scheduler carrying the configured shared secret.

    The public API service must stay reachable for GitHub and Telegram webhooks, so
    this private trigger is explicitly authenticated in the application layer.  The
    missing-secret branch intentionally fails closed rather than accepting a request
    during an incomplete deployment.
    """
    secret = settings.SCHEDULER_SHARED_SECRET
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler trigger is not configured",
        )
    if not x_scheduler_secret or not hmac.compare_digest(x_scheduler_secret, secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheduler credentials")
    return await opportunity_service.fetch_and_publish_opportunities()
