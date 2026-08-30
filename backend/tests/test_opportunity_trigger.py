from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.dependencies import get_opportunity_service
from app.main import app


class StubOpportunityService:
    def __init__(self) -> None:
        self.calls = 0

    async def fetch_and_publish_opportunities(self):
        self.calls += 1
        return {"status": "success", "fetched": 1, "published": 1}


def _settings(secret: str | None) -> Settings:
    return Settings(_env_file=None, SCHEDULER_SHARED_SECRET=secret)


def test_scheduler_trigger_fails_closed_and_only_calls_service_after_constant_time_secret_check():
    service = StubOpportunityService()
    app.dependency_overrides[get_settings] = lambda: _settings("scheduler-secret")
    app.dependency_overrides[get_opportunity_service] = lambda: service
    try:
        client = TestClient(app, raise_server_exceptions=False)
        assert client.post("/api/v1/trigger/opportunities").status_code == 401
        assert client.post(
            "/api/v1/trigger/opportunities", headers={"X-Scheduler-Secret": "wrong"}
        ).status_code == 401
        accepted = client.post(
            "/api/v1/trigger/opportunities", headers={"X-Scheduler-Secret": "scheduler-secret"}
        )
    finally:
        app.dependency_overrides.clear()

    assert accepted.status_code == 200
    assert accepted.json()["published"] == 1
    assert service.calls == 1


def test_scheduler_trigger_returns_503_when_deployment_has_no_secret():
    service = StubOpportunityService()
    app.dependency_overrides[get_settings] = lambda: _settings(None)
    app.dependency_overrides[get_opportunity_service] = lambda: service
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/trigger/opportunities", headers={"X-Scheduler-Secret": "anything"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert service.calls == 0
