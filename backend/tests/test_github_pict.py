from __future__ import annotations

import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.webhooks.github import receive_github_webhook
from app.models.github import GitHubEventEnvelope
from app.services.github_service import GitHubService
from tests.fakes import FakeFirestore
from workers.github_worker import decode_github_event_envelope


class DummyResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data
        self.text = text

    def json(self):
        return self._data


class DummyHTTP:
    def __init__(self, *, posts=(), gets=(), deletes=()):
        self.posts = list(posts)
        self.gets = list(gets)
        self.deletes = list(deletes)
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.posts.pop(0)

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.gets.pop(0)

    async def delete(self, url, **kwargs):
        self.calls.append(("DELETE", url, kwargs))
        return self.deletes.pop(0) if self.deletes else DummyResponse(204)


class DummySecretClient:
    def create_secret(self, **kwargs):
        return kwargs

    def add_secret_version(self, **kwargs):
        return kwargs

    def delete_secret(self, **kwargs):
        return kwargs


class DummyFuture:
    def result(self, timeout=None):
        return timeout


class DummyPublisher:
    def __init__(self):
        self.published = []

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"

    def publish(self, topic, **kwargs):
        self.published.append((topic, kwargs))
        return DummyFuture()


class DummyRequest:
    def __init__(self, body):
        self._body = body

    async def body(self):
        return self._body


def make_service(db=None, http=None, webhook_base_url=None):
    settings = SimpleNamespace(
        GCP_PROJECT_ID="mark-i-test",
        GITHUB_CLIENT_ID="client-id",
        GITHUB_CLIENT_SECRET="client-secret",
        GITHUB_WEBHOOK_SECRET="webhook-secret",
        FRONTEND_URL="http://localhost:3000",
        WEBHOOK_BASE_URL=webhook_base_url,
        PUBSUB_GITHUB_TOPIC="github-events",
    )
    return GitHubService(
        db=db or FakeFirestore(),
        httpx_client=http or DummyHTTP(),
        secret_client=DummySecretClient(),
        pubsub_publisher=DummyPublisher(),
        settings=settings,
    )


def test_auth_url_contains_oauth_parameters_and_stores_ten_minute_state():
    db = FakeFirestore()
    db.collection("users").document("user-1").set({})
    service = make_service(db=db)
    before = datetime.now(timezone.utc)

    url = service.generate_auth_url("user-1")
    saved = db.collection("users").document("user-1").get().to_dict()["githubOAuthState"]

    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=client-id" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fgithub%2Fcallback" in url
    assert f"state={saved['state']}" in url
    assert before + timedelta(minutes=9, seconds=59) <= saved["expiresAt"] <= before + timedelta(minutes=10, seconds=1)


@pytest.mark.parametrize(
    ("saved_state", "provided_state", "expected_code"),
    [
        (None, "missing", "INVALID_STATE"),
        ({"state": "expected", "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=1)}, "other", "INVALID_STATE"),
        ({"state": "expected", "expiresAt": datetime.now(timezone.utc) - timedelta(seconds=1)}, "expected", "EXPIRED_STATE"),
    ],
)
def test_callback_rejects_missing_mismatched_and_expired_state(saved_state, provided_state, expected_code):
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"githubOAuthState": saved_state})
    service = make_service(db=db)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.exchange_code("user-1", "oauth-code", provided_state))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("token_response", "expected_status", "expected_code"),
    [
        (DummyResponse(503, {}), 502, "GITHUB_API_ERROR"),
        (DummyResponse(200, {"error_description": "bad code"}), 400, "OAUTH_FAILED"),
    ],
)
def test_callback_maps_github_token_exchange_errors(token_response, expected_status, expected_code):
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {
            "githubOAuthState": {
                "state": "state-1",
                "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=1),
            }
        }
    )
    service = make_service(db=db, http=DummyHTTP(posts=[token_response]))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.exchange_code("user-1", "oauth-code", "state-1"))

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail["error"]["code"] == expected_code


def test_successful_callback_updates_user_and_returns_repositories(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {
            "githubOAuthState": {
                "state": "state-1",
                "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=1),
            },
            "connectedRepos": ["alex/existing"],
        }
    )
    http = DummyHTTP(
        posts=[DummyResponse(200, {"access_token": "token-1"})],
        gets=[
            DummyResponse(200, {"login": "alex"}),
            DummyResponse(
                200,
                [
                    {"full_name": "alex/existing", "private": False},
                    {"full_name": "alex/new", "private": True},
                ],
            ),
        ],
    )
    service = make_service(db=db, http=http)
    monkeypatch.setattr(service, "_store_token", lambda uid, token: f"github-token-{uid}")

    result = asyncio.run(service.exchange_code("user-1", "oauth-code", "state-1"))
    saved = db.collection("users").document("user-1").get().to_dict()

    assert result["githubUsername"] == "alex"
    assert [repo.fullName for repo in result["repos"]] == ["alex/existing", "alex/new"]
    assert [repo.connected for repo in result["repos"]] == [True, False]
    assert saved["githubConnected"] is True
    assert saved["githubOAuthState"] is None


def test_select_repos_rejects_invalid_name(monkeypatch):
    service = make_service()
    monkeypatch.setattr(service, "_get_token", lambda uid: "token")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.select_repos("user-1", ["not-a-full-name"]))
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "INVALID_REPO"


def test_select_repos_without_webhook_url_saves_repos_without_registration(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set({"connectedRepos": [], "webhookIds": {}})
    service = make_service(db=db, webhook_base_url=None)
    monkeypatch.setattr(service, "_get_token", lambda uid: "token")

    result = asyncio.run(service.select_repos("user-1", ["alex/repo"]))

    assert result == {"connectedRepos": ["alex/repo"], "webhooksRegistered": 0}


def test_empty_repo_selection_removes_existing_webhooks(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {"connectedRepos": ["alex/old"], "webhookIds": {"alex/old": "42"}}
    )
    http = DummyHTTP(deletes=[DummyResponse(204)])
    service = make_service(db=db, http=http)
    monkeypatch.setattr(service, "_get_token", lambda uid: "token")

    result = asyncio.run(service.select_repos("user-1", []))

    assert result["connectedRepos"] == []
    assert any(call[0] == "DELETE" and call[1].endswith("/alex/old/hooks/42") for call in http.calls)


def test_mixed_repo_selection_adds_and_removes_webhooks(monkeypatch):
    db = FakeFirestore()
    db.collection("users").document("user-1").set(
        {
            "connectedRepos": ["alex/keep", "alex/remove"],
            "webhookIds": {"alex/keep": "1", "alex/remove": "2"},
        }
    )
    http = DummyHTTP(posts=[DummyResponse(201, {"id": 3})], deletes=[DummyResponse(204)])
    service = make_service(db=db, http=http, webhook_base_url="https://backend.example")
    monkeypatch.setattr(service, "_get_token", lambda uid: "token")

    result = asyncio.run(service.select_repos("user-1", ["alex/keep", "alex/add"]))
    saved = db.collection("users").document("user-1").get().to_dict()

    assert set(result["connectedRepos"]) == {"alex/keep", "alex/add"}
    assert result["webhooksRegistered"] == 1
    assert saved["webhookIds"] == {"alex/keep": "1", "alex/add": "3"}


def test_disconnect_is_idempotent_for_missing_user():
    asyncio.run(make_service().disconnect("missing"))


@pytest.mark.parametrize("valid", [True, False])
def test_webhook_hmac_signature_validation(valid):
    service = make_service()
    body = b'{"repository":{"full_name":"alex/repo"}}'
    signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    header = f"sha256={signature}" if valid else "sha256=invalid"
    assert service.verify_webhook_signature(body, header) is valid


def test_webhook_rejects_malformed_json_after_valid_signature():
    class Service:
        def verify_webhook_signature(self, body, signature):
            return True

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            receive_github_webhook(
                request=DummyRequest(b"not-json"),
                x_hub_signature_256="sha256=valid",
                x_github_event="push",
                x_github_delivery="delivery-1",
                service=Service(),
            )
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "BAD_REQUEST"


def test_webhook_publishes_valid_payload_and_delivery_id():
    calls = []

    class Service:
        def verify_webhook_signature(self, body, signature):
            return True

        def publish_event(self, **kwargs):
            calls.append(kwargs)

    response = asyncio.run(
        receive_github_webhook(
            request=DummyRequest(b'{"repository":{"full_name":"alex/repo"}}'),
            x_hub_signature_256="sha256=valid",
            x_github_event="push",
            x_github_delivery="delivery-1",
            service=Service(),
        )
    )

    assert response == {"accepted": True, "deliveryId": "delivery-1"}
    assert calls == [
        {
            "event_type": "push",
            "delivery_id": "delivery-1",
            "payload": {"repository": {"full_name": "alex/repo"}},
        }
    ]


def test_event_envelope_round_trips_without_key_translation():
    envelope = GitHubEventEnvelope(
        deliveryId="delivery-1",
        eventType="push",
        uid="user-1",
        repoFullName="Alex/Repo",
        payload={"repository": {"full_name": "Alex/Repo"}},
    )

    parsed = GitHubEventEnvelope.model_validate_json(envelope.model_dump_json())

    assert parsed == envelope
    assert parsed.schemaVersion == 1
    assert parsed.receivedAt.tzinfo is not None


def test_worker_decodes_the_publisher_envelope_without_manual_field_mapping():
    envelope = GitHubEventEnvelope(
        deliveryId="delivery-1",
        eventType="push",
        uid="user-1",
        repoFullName="alex/repo",
        payload={"repository": {"full_name": "alex/repo"}},
    )

    decoded = decode_github_event_envelope(envelope.model_dump_json().encode("utf-8"))

    assert decoded == envelope


@pytest.mark.parametrize(
    "changes",
    [
        {"uid": ""},
        {"schemaVersion": 2},
        {"receivedAt": "2026-08-29T12:00:00"},
    ],
)
def test_event_envelope_rejects_invalid_or_unsupported_contract(changes):
    data = {
        "deliveryId": "delivery-1",
        "eventType": "push",
        "uid": "user-1",
        "repoFullName": "alex/repo",
        "payload": {},
        "receivedAt": "2026-08-29T12:00:00+00:00",
    }
    data.update(changes)

    with pytest.raises(ValidationError):
        GitHubEventEnvelope.model_validate(data)


def test_publish_event_fans_out_one_validated_envelope_per_connected_user():
    db = FakeFirestore()
    db.collection("users").document("user-z").set({"connectedRepos": ["other/repo", "Alex/Repo"]})
    db.collection("users").document("user-a").set({"connectedRepos": ["alex/repo"]})
    db.collection("users").document("user-other").set({"connectedRepos": ["elsewhere/repo"]})
    service = make_service(db=db)

    uids = service.publish_event(
        event_type="push",
        delivery_id="delivery-1",
        payload={"repository": {"full_name": "alex/repo"}, "commits": []},
    )

    assert uids == ["user-a", "user-z"]
    messages = [GitHubEventEnvelope.model_validate_json(item[1]["data"]) for item in service._pubsub_publisher.published]
    assert [message.uid for message in messages] == ["user-a", "user-z"]
    assert all(message.deliveryId == "delivery-1" for message in messages)
    assert all(message.eventType == "push" for message in messages)


def test_publish_event_accepts_unconnected_repository_without_publishing(caplog):
    service = make_service(db=FakeFirestore())

    assert service.publish_event("push", "delivery-1", {"repository": {"full_name": "alex/repo"}}) == []
    assert service._pubsub_publisher.published == []
    assert "unconnected repository" in caplog.text


def test_publish_event_rejects_missing_repository_name():
    with pytest.raises(HTTPException) as exc_info:
        make_service().publish_event("push", "delivery-1", {"repository": {}})

    assert exc_info.value.status_code == 400
