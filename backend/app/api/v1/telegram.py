from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.dependencies import get_db, get_current_user_id
from app.models.telegram import LinkCodeResponse, SuccessResponse
from app.services.telegram_service import TelegramService

router = APIRouter(tags=["Telegram"])

@router.post("/telegram/link", response_model=LinkCodeResponse)
async def generate_telegram_link(
    uid: str = Depends(get_current_user_id),
    db: FirestoreClient = Depends(get_db)
):
    """
    Generates a temporary code to link a Telegram account.
    """
    telegram_service = TelegramService(db)
    code = telegram_service.generate_link_code(uid)
    return LinkCodeResponse(code=code)

@router.delete("/telegram/link", response_model=SuccessResponse)
async def unlink_telegram(
    uid: str = Depends(get_current_user_id),
    db: FirestoreClient = Depends(get_db)
):
    """
    Unlinks the Telegram account from the current user.
    """
    user_ref = db.collection("users").document(uid)
    user_ref.update({
        "telegramLinked": False,
        "telegramUserId": None,
        "telegramUsername": None
    })
    return SuccessResponse(success=True)
