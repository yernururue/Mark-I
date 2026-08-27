from fastapi import APIRouter, Depends
from google.cloud.firestore_v1.client import Client as FirestoreClient
from app.dependencies import get_db
from app.services.opportunity_service import OpportunityService

router = APIRouter(tags=["Triggers"])

@router.post("/trigger/opportunities")
async def trigger_opportunities(db: FirestoreClient = Depends(get_db)):
    """
    Эндпоинт для запуска сбора opportunities.
    В продакшене этот эндпоинт должен дергаться по расписанию (Cloud Scheduler).
    Для безопасности его можно закрыть отдельным токеном.
    """
    opportunity_service = OpportunityService(db)
    result = await opportunity_service.fetch_and_publish_opportunities()
    return result
