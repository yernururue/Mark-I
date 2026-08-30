"""Stage 3 contract tests: canonical OpenAPI, API edge and Firestore semantics."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.api.v1.chat import router as chat_router
from app.dependencies import (
    get_chat_service,
    get_current_user_id,
    get_dashboard_service,
    get_observation_service,
    get_telegram_service,
)
from app.main import app
from app.models.chat import ChatResponse, MessagesResponse
from app.models.telegram import LinkCodeResponse
from app.services.chat_service import ChatService
from app.services.dashboard_service import DashboardService
from app.services.observation_service import ObservationService
from app.services.telegram_service import TelegramService
from app.services.user_service import UserService
from app.models.user import CreateProfileRequest
from tests.fakes import FakeFirestore


ROOT = Path(__file__).parents[2]
CANONICAL_OPENAPI = ROOT / "openapi.yaml"


def _resolve(spec: dict, schema: dict) -> dict:
    while "$ref" in schema:
        schema = spec["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def _shape(spec: dict, schema: dict) -> tuple[set[str], set[str]]:
    resolved = _resolve(spec, schema)
    return set(resolved.get("properties", {})), set(resolved.get("required", []))


def _json_schema(operation: dict, kind: str) -> dict | None:
    if kind == "request":
        return operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
    for code, response in operation["responses"].items():
        if str(code).startswith("2"):
            return response.get("content", {}).get("application/json", {}).get("schema")
    return None


def _resolve_response(spec: dict, response: dict) -> dict:
    while "$ref" in response:
        response = spec["components"]["responses"][response["$ref"].rsplit("/", 1)[-1]]
    return response


def _material_schema(spec: dict, schema: dict) -> dict:
    """Keep only contract semantics, recursively resolving generated refs.

    Titles, examples and implementation prose do not affect clients. Required
    fields, nullability, enums, bounds, defaults and nested response shapes do.
    """
    # Pydantic uses a reference plus a sibling ``default`` for enum fields;
    # OpenAPI permits that composition, so retain those sibling constraints.
    if "$ref" in schema:
        referenced = _resolve(spec, {"$ref": schema["$ref"]})
        schema = {**referenced, **{key: value for key, value in schema.items() if key != "$ref"}}
    if "anyOf" in schema:
        non_null = [item for item in schema["anyOf"] if item.get("type") != "null"]
        if len(non_null) == 1 and len(non_null) != len(schema["anyOf"]):
            result = _material_schema(spec, non_null[0])
            result["nullable"] = True
            if "default" in schema:
                result["default"] = schema["default"]
            return result
    result = {
        key: schema[key]
        for key in (
            "type", "format", "enum", "minimum", "maximum", "minLength",
            "maxLength", "pattern", "default", "nullable",
        )
        if key in schema
    }
    if "properties" in schema:
        result["properties"] = {
            name: _material_schema(spec, value)
            for name, value in schema["properties"].items()
        }
    if "required" in schema:
        result["required"] = sorted(schema["required"])
    if "items" in schema:
        result["items"] = _material_schema(spec, schema["items"])
    if "additionalProperties" in schema:
        value = schema["additionalProperties"]
        result["additionalProperties"] = (
            _material_schema(spec, value) if isinstance(value, dict) else value
        )
    return result


def _response_schema(spec: dict, response: dict) -> dict | None:
    response = _resolve_response(spec, response)
    return response.get("content", {}).get("application/json", {}).get("schema")


def test_canonical_openapi_matches_fastapi_paths_methods_and_top_level_shapes():
    canonical = yaml.safe_load(CANONICAL_OPENAPI.read_text())
    generated = app.openapi()
    canonical_paths = canonical["paths"]
    generated_paths = generated["paths"]
    assert set(generated_paths) == set(canonical_paths)

    methods = {"get", "post", "patch", "delete"}
    for path, canonical_path in canonical_paths.items():
        expected_methods = {method for method in canonical_path if method in methods}
        actual_methods = {method for method in generated_paths[path] if method in methods}
        assert actual_methods == expected_methods, path
        for method in expected_methods:
            expected_operation = canonical_path[method]
            actual_operation = generated_paths[path][method]
            for kind in ("request", "response"):
                expected_schema = _json_schema(expected_operation, kind)
                actual_schema = _json_schema(actual_operation, kind)
                assert bool(actual_schema) == bool(expected_schema), (path, method, kind)
                if expected_schema:
                    assert _shape(generated, actual_schema) == _shape(canonical, expected_schema), (path, method, kind)


def test_canonical_openapi_matches_generated_security_parameters_and_deep_schemas():
    canonical = yaml.safe_load(CANONICAL_OPENAPI.read_text())
    generated = app.openapi()
    for path, canonical_path in canonical["paths"].items():
        for method, expected in canonical_path.items():
            if method not in {"get", "post", "patch", "delete"}:
                continue
            actual = generated["paths"][path][method]
            assert actual["operationId"] == expected["operationId"], (path, method)
            assert actual.get("security") == expected.get("security"), (path, method)
            expected_parameters = {
                (parameter["name"].lower(), parameter["in"]): (
                    parameter.get("required", False),
                    _material_schema(canonical, parameter["schema"]),
                )
                for parameter in expected.get("parameters", [])
            }
            actual_parameters = {
                (parameter["name"].lower(), parameter["in"]): (
                    parameter.get("required", False),
                    _material_schema(generated, parameter["schema"]),
                )
                for parameter in actual.get("parameters", [])
            }
            assert actual_parameters == expected_parameters, (path, method)
            expected_request = _json_schema(expected, "request")
            actual_request = _json_schema(actual, "request")
            assert bool(actual_request) == bool(expected_request), (path, method, "request")
            if expected_request:
                assert actual["requestBody"].get("required") is expected["requestBody"].get("required")
                assert _material_schema(generated, actual_request) == _material_schema(canonical, expected_request)
            assert set(actual["responses"]) == set(expected["responses"]), (path, method, "responses")
            for status, expected_response in expected["responses"].items():
                actual_schema = _response_schema(generated, actual["responses"][status])
                expected_schema = _response_schema(canonical, expected_response)
                assert bool(actual_schema) == bool(expected_schema), (path, method, status)
                if expected_schema:
                    assert _material_schema(generated, actual_schema) == _material_schema(
                        canonical, expected_schema
                    ), (path, method, status)


@pytest.mark.parametrize(
    ("canonical_component", "generated_component"),
    [
        ("UserProfile", "UserProfile"),
        ("DashboardResponse", "DashboardResponse"),
        ("DashboardStats", "DashboardStats"),
        ("Decision", "Decision"),
        ("ObservationsResponse", "ObservationsResponse"),
        ("ChatRequest", "ChatRequest"),
        ("ChatResponse", "ChatResponse"),
        ("MessagesResponse", "MessagesResponse"),
        ("TelegramLinkResponse", "TelegramLinkResponse"),
    ],
)
def test_critical_component_shapes_match_canonical_openapi(canonical_component: str, generated_component: str):
    canonical = yaml.safe_load(CANONICAL_OPENAPI.read_text())
    generated = app.openapi()
    assert _shape(generated, {"$ref": f"#/components/schemas/{generated_component}"}) == _shape(
        canonical, {"$ref": f"#/components/schemas/{canonical_component}"}
    )


def test_validation_and_domain_errors_use_documented_envelope():
    db = FakeFirestore()
    app.dependency_overrides[get_current_user_id] = lambda: "missing"
    app.dependency_overrides[get_chat_service] = lambda: ChatService(db)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        invalid = client.post("/api/v1/chat", json={"message": "", "channel": "web"})
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
        missing = client.post("/api/v1/chat", json={"message": "Hello", "channel": "web"})
        assert missing.status_code == 404
        assert missing.json() == {"error": {"code": "NOT_FOUND", "message": "User profile not found"}}
    finally:
        app.dependency_overrides.clear()


def test_framework_404_and_405_use_the_same_error_envelope():
    client = TestClient(app, raise_server_exceptions=False)
    missing = client.get("/does-not-exist")
    wrong_method = client.post("/health")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert wrong_method.status_code == 405
    assert wrong_method.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def _create_user(db: FakeFirestore) -> None:
    UserService(db).create_profile(
        "user-1",
        "alex@example.com",
        CreateProfileRequest(displayName="Alex", goal="Become a backend developer", intensity="normal"),
    )


def test_observation_cursor_filters_and_boundaries_are_stable():
    db = FakeFirestore()
    service = ObservationService(db)
    now = datetime.now(timezone.utc)
    collection = db.collection("users").document("user-1").collection("observations")
    for identifier, source, concept, created_at in (
        ("obs-c", "github", "recursion", now),
        ("obs-b", "github", "recursion", now),
        ("obs-a", "chat", "recursion", now),
        ("obs-old", "github", "testing", now - timedelta(seconds=1)),
    ):
        collection.document(identifier).set(
            {"id": identifier, "source": source, "summary": identifier, "concept": concept,
             "sentiment": "neutral", "significanceScore": 5, "createdAt": created_at}
        )
    first = service.get_observations("user-1", limit=1, source="github")
    second = service.get_observations("user-1", limit=1, source="github", cursor=first.nextCursor)
    assert [item.id for item in first.observations] == ["obs-c"]
    assert [item.id for item in second.observations] == ["obs-b"]
    assert first.hasMore is True and second.hasMore is True
    assert {item.id for item in first.observations}.isdisjoint(item.id for item in second.observations)
    concept_page = service.get_observations("user-1", limit=10, concept="recursion")
    assert {item.id for item in concept_page.observations} == {"obs-a", "obs-b", "obs-c"}


def test_chat_history_is_service_owned_channel_filtered_and_cursor_stable(monkeypatch):
    db = FakeFirestore()
    _create_user(db)
    now = datetime.now(timezone.utc)
    messages = db.collection("users").document("user-1").collection("messages")
    for identifier, channel in (("msg-a", "web"), ("msg-b", "web"), ("msg-c", "telegram")):
        messages.document(identifier).set(
            {"id": identifier, "role": "user", "channel": channel, "text": identifier, "createdAt": now}
        )
    service = ChatService(db, transactional_runner=lambda function: function)
    first = service.get_messages("user-1", limit=1, channel="web")
    second = service.get_messages("user-1", limit=1, channel="web", cursor=first.nextCursor)
    assert [message.id for message in first.messages] == ["msg-a"]
    assert [message.id for message in second.messages] == ["msg-b"]
    assert first.hasMore is True


def test_chat_route_returns_persisted_ids_and_documented_response_shape():
    class FakeChatService:
        async def process_message(self, uid: str, text: str, channel: str, turn_id: str | None = None) -> ChatResponse:
            assert (uid, text, channel) == ("user-1", "Hello", "web")
            assert turn_id is None
            return ChatResponse(response="Hi", messageId="msg-1", agentMessageId="msg-2")

        def get_messages(self, **_: object) -> MessagesResponse:
            return MessagesResponse(messages=[], nextCursor=None, hasMore=False)

    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_chat_service] = FakeChatService
    try:
        response = TestClient(app).post("/api/v1/chat", json={"message": "Hello", "channel": "web"})
        assert response.status_code == 200
        assert response.json() == {"response": "Hi", "messageId": "msg-1", "agentMessageId": "msg-2"}
    finally:
        app.dependency_overrides.clear()


def test_telegram_code_is_transactional_single_use_and_unlink_is_idempotent():
    db = FakeFirestore()
    _create_user(db)
    service = TelegramService(db, transactional_runner=lambda function: function)
    link = service.generate_link_code("user-1")
    assert service.validate_and_link(link.code, telegram_user_id=42, telegram_chat_id=-100, username="alex")
    user = db.collection("users").document("user-1").get().to_dict()
    assert user["telegramUserId"] == 42
    assert user["telegramChatId"] == -100
    assert service.validate_and_link(link.code, telegram_user_id=99, telegram_chat_id=99) is False
    assert service.unlink("user-1") is True
    assert service.unlink("user-1") is True
    user = db.collection("users").document("user-1").get().to_dict()
    assert user["telegramUserId"] is None and user["telegramChatId"] is None


def test_dashboard_uses_persisted_decisions_and_stats_not_router_mocks():
    db = FakeFirestore()
    _create_user(db)
    observation = ObservationService(db).create_observation("user-1", "github", "Useful work", "testing", "positive", 8)
    from app.services.decision_service import DecisionService
    DecisionService(db).evaluate_and_log("user-1", observation.id, 8, "normal", [])
    dashboard = DashboardService(db).get_dashboard("user-1", observation_limit=10, decision_limit=1)
    assert dashboard.stats.totalObservations == 1
    assert dashboard.stats.totalSkills == 0
    assert dashboard.recentDecisions[0].action == "notified"
    assert dashboard.recentDecisions[0].threshold == 5
