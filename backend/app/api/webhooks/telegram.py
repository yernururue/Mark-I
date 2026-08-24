import os
from fastapi import APIRouter, Depends, Request
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.dependencies import get_db
from telegrambot.handlers import process_telegram_update

router = APIRouter(tags=["Webhooks"])

@router.post("/webhooks/telegram")
async def telegram_webhook(request: Request, db: FirestoreClient = Depends(get_db)):
    """
    Receives updates from Telegram.
    For security, you'd ideally check the secret token in the headers 
    (X-Telegram-Bot-Api-Secret-Token) if configured.
    """
    update_data = await request.json()
    
    # Process asynchronously in the background or await it directly
    # For MVP, waiting for it is fine since it's fast
    await process_telegram_update(update_data, db)
    
    # Telegram requires 200 OK to stop retrying
    return {"status": "ok"}
