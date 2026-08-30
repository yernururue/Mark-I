from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.webhooks import telegram as telegram_webhook_module
from app.config import Settings, get_settings
from app.dependencies import get_db
from app.main import app
from app.services.telegram_service import TelegramService
from tests.fakes import FakeFirestore


def _settings(secret: str | None = "webhook-secret") -> Settings:
    return Settings(
        _env_file=None,
        GCP_PROJECT_ID="test-project",
        GITHUB_CLIENT_ID="client",
        GITHUB_CLIENT_SECRET="client-secret",
        GITHUB_WEBHOOK_SECRET="github-secret",
        TELEGRAM_BOT_TOKEN="token",
        TELEGRAM_WEBHOOK_SECRET=secret,
    )


def test_webhook_requires_configured_constant_time_secret_and_processes_delivery_once(monkeypatch):
    db = FakeFirestore()
    process = AsyncMock()
    monkeypatch.setattr(telegram_webhook_module, "process_telegram_update", process)

    class TestTelegramService(TelegramService):
        def __init__(self, database, settings):
            super().__init__(database, settings, transactional_runner=lambda function: function)

    monkeypatch.setattr(telegram_webhook_module, "TelegramService", TestTelegramService)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = _settings
    try:
        client = TestClient(app, raise_server_exceptions=False)
        body = {"update_id": 701, "message": {"chat": {"id": 1}, "text": "/start"}}
        assert client.post("/api/v1/webhooks/telegram", json=body).status_code == 401
        assert client.post(
            "/api/v1/webhooks/telegram",
            json=body,
            headers={"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"},
        ).status_code == 200
        assert client.post(
            "/api/v1/webhooks/telegram",
            json=body,
            headers={"X-Telegram-Bot-Api-Secret-Token": "webhook-secret"},
        ).status_code == 200
    finally:
        app.dependency_overrides.clear()
    assert process.await_count == 1


def test_webhook_fails_closed_when_secret_is_not_configured():
    app.dependency_overrides[get_db] = FakeFirestore
    app.dependency_overrides[get_settings] = lambda: _settings(None)
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/webhooks/telegram",
            json={"update_id": 702},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
