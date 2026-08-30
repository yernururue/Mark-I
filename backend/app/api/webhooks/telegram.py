"""Authenticated, idempotent Telegram webhook ingestion."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.config import Settings, get_settings
from app.api.contracts import error_responses
from app.dependencies import get_db
from app.models.common import TelegramWebhookResponse
from app.services.telegram_service import TelegramService
from telegrambot.handlers import process_telegram_update

router = APIRouter(tags=["Webhooks"])


@router.post(
    "/webhooks/telegram",
    response_model=TelegramWebhookResponse,
    responses=error_responses(400, 401, 422, 503),
    operation_id="receiveTelegramWebhook",
)
async def telegram_webhook(
    update_data: dict = Body(...),
    x_telegram_bot_api_secret_token: str = Header(default=None),
    db: FirestoreClient = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Accept only configured Telegram deliveries and process each update once."""
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=503, detail="Telegram webhook is not configured")
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        secret, x_telegram_bot_api_secret_token
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    update_id = update_data.get("update_id")
    if not isinstance(update_id, int) or update_id < 0:
        raise HTTPException(status_code=400, detail="Telegram update_id is required")
    service = TelegramService(db, settings=settings)
    claim = service.claim_update(update_id)
    if claim == "completed":
        return TelegramWebhookResponse(ok=True)
    if claim == "busy":
        # A non-2xx response asks Telegram to retry after the existing lease;
        # silently ACKing here could lose the update if that handler dies.
        raise HTTPException(status_code=503, detail="Telegram update is being processed")
    try:
        await process_telegram_update(update_data, db)
    except Exception:
        service.release_update(update_id)
        raise
    service.complete_update(update_id)
    return TelegramWebhookResponse(ok=True)
