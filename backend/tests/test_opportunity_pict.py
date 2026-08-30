from __future__ import annotations

import asyncio
import json

from app.services import opportunity_service as opportunity_module  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


class FakePublisher:
    def __init__(self):
        self.messages = []

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"

    def publish(self, topic, *, data):
        self.messages.append((topic, json.loads(data)))


class FakeResponse:
    def __init__(self, articles=None, error=None):
        self._articles = articles
        self._error = error

    def raise_for_status(self):
        if self._error:
            raise self._error

    def json(self):
        return self._articles


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        assert url == "https://dev.to/api/articles?per_page=10"
        return self.response


def build_service(monkeypatch, db, response):
    publisher = FakePublisher()
    monkeypatch.setattr(opportunity_module.pubsub_v1, "PublisherClient", lambda: publisher)
    monkeypatch.setattr(
        opportunity_module.httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(response),
    )
    return opportunity_module.OpportunityService(db), publisher


def test_current_articles_are_published_and_recorded_as_collected(monkeypatch):
    db = FakeFirestore()
    articles = [
        {
            "id": 101,
            "url": "https://dev.to/article-101",
            "title": "Learn React",
            "description": "Hooks and state",
            "tag_list": ["react"],
        }
    ]
    service, publisher = build_service(monkeypatch, db, FakeResponse(articles))

    result = asyncio.run(service.fetch_and_publish_opportunities())

    assert result == {"status": "success", "fetched": 1, "published": 1}
    assert publisher.messages[0][1]["eventId"] == "devto-101"
    collected = db.collection("collected_opportunities").document("devto-101").get()
    assert collected.exists
    assert collected.to_dict()["source"] == "devto"


def test_seen_current_articles_are_republished_for_newly_eligible_users(monkeypatch):
    db = FakeFirestore()
    db.collection("collected_opportunities").document("devto-101").set({"eventId": "devto-101"})
    articles = [{"id": 101, "url": "https://dev.to/article-101", "title": "Learn React"}]
    service, publisher = build_service(monkeypatch, db, FakeResponse(articles))

    result = asyncio.run(service.fetch_and_publish_opportunities())

    assert result == {"status": "success", "fetched": 1, "published": 1}
    assert publisher.messages[0][1]["eventId"] == "devto-101"


def test_devto_timeout_or_error_returns_error_status(monkeypatch):
    db = FakeFirestore()
    service, publisher = build_service(monkeypatch, db, FakeResponse(error=TimeoutError("timeout")))

    result = asyncio.run(service.fetch_and_publish_opportunities())

    assert result["status"] == "error"
    assert "timeout" in result["message"]
    assert publisher.messages == []
