import os
from fastapi import APIRouter, Body, Depends, Request, Header, HTTPException
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.dependencies import get_db
from telegrambot.handlers import process_telegram_update
from app.models.common import TelegramWebhookResponse

router = APIRouter(tags=["Webhooks"])

@router.post("/webhooks/telegram", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    request: Request,
    update_data: dict = Body(...),
    x_telegram_bot_api_secret_token: str = Header(None),
    db: FirestoreClient = Depends(get_db)
):
    """
    Receives updates from Telegram.
    For security, checks the secret token in the headers 
    (X-Telegram-Bot-Api-Secret-Token) if configured.
    """
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Process asynchronously in the background or await it directly
    # For MVP, waiting for it is fine since it's fast
    await process_telegram_update(update_data, db)
    
    # Telegram requires 200 OK to stop retrying
    return TelegramWebhookResponse(ok=True)
