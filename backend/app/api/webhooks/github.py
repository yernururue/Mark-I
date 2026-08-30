"""
github.py — Webhook receiver для событий от GitHub.
"""
from typing import Literal

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request

from app.api.contracts import error_responses
from app.dependencies import get_github_service
from app.services.github_service import GitHubService
from app.models.common import GitHubWebhookResponse

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])





@router.post("/github", response_model=GitHubWebhookResponse, responses=error_responses(401, 422), operation_id="receiveGithubWebhook")
async def receive_github_webhook(
    request: Request,
    payload: dict = Body(...),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
    x_github_event: Literal["push", "pull_request", "pull_request_review", "issues", "issue_comment", "create"] = Header(..., alias="X-GitHub-Event"),
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

    # 3. FastAPI has already validated the JSON object while preserving raw bytes for HMAC.
    # 4. Публикуем событие в Pub/Sub
    service.publish_event(
        event_type=x_github_event,
        delivery_id=x_github_delivery,
        payload=payload,
    )

    return GitHubWebhookResponse(accepted=True, deliveryId=x_github_delivery)
