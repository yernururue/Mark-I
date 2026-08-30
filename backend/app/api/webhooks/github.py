"""
github.py — Webhook receiver для событий от GitHub.
"""
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from google.cloud.firestore_v1.client import Client as FirestoreClient
import httpx
from google.cloud import pubsub_v1, secretmanager

from app.dependencies import get_github_service
from app.services.github_service import GitHubService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])





@router.post("/github")
async def receive_github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    service: GitHubService = Depends(get_github_service),
):
    """Приемник вебхуков от GitHub с HMAC валидацией и отправкой в Pub/Sub (POST /api/v1/webhooks/github)."""
    # 1. Читаем сырое тело запроса для правильной проверки HMAC подписи
    raw_body = await request.body()

    # 2. Проверяем HMAC-SHA256 подпись
    if not service.verify_webhook_signature(raw_body, x_hub_signature_256):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Недействительная подпись HMAC"}},
        )

    # 3. Парсим JSON тело
    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "BAD_REQUEST", "message": "Невалидный JSON payload"}},
        )

    # 4. Публикуем событие в Pub/Sub
    service.publish_event(
        event_type=x_github_event,
        delivery_id=x_github_delivery,
        payload=payload,
    )

    return {"accepted": True, "deliveryId": x_github_delivery}
