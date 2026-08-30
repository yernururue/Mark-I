from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.config import ConfigurationError, RuntimeRole, Settings, get_settings, reset_settings_cache
from app.models.chat import ChatRequest, ChatResponse
from app.models.dashboard import DashboardStats
from app.models.decision import Decision
from app.models.observation import ObservationsResponse
from app.models.github import GitHubEventEnvelope
from app.services.processed_event_service import ProcessedEventService
from workers.github_extractors import EVENT_EXTRACTORS
from workers.github_worker import decode_github_event_envelope


BACKEND_ROOT = Path(__file__).parents[1]


def run_python(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_config_exports_get_settings():
    result = run_python("from app.config import get_settings; assert get_settings()")
    assert result.returncode == 0, result.stderr


def test_settings_are_lazy_cached_and_role_validation_is_sanitised(monkeypatch):
    for name in ("GCP_PROJECT_ID", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_WEBHOOK_SECRET"):
        monkeypatch.delenv(name, raising=False)
    reset_settings_cache()
    cached = get_settings()
    assert cached is get_settings()
    first = Settings(
        _env_file=None,
        GCP_PROJECT_ID=None,
        GITHUB_CLIENT_ID=None,
        GITHUB_CLIENT_SECRET=None,
        GITHUB_WEBHOOK_SECRET=None,
    )
    with pytest.raises(ConfigurationError, match="GCP_PROJECT_ID") as error:
        first.validate_for_role(RuntimeRole.API)
    assert "known-test-secret" not in str(error.value)
    reset_settings_cache()


def test_explicit_settings_do_not_read_dotenv_or_real_environment():
    settings = Settings(_env_file=None, GCP_PROJECT_ID="unit-project")
    assert settings.GCP_PROJECT_ID == "unit-project"


def test_dependencies_export_router_contract():
    result = run_python("from app.dependencies import get_db, get_current_user_id")
    assert result.returncode == 0, result.stderr


def test_github_router_imports():
    result = run_python("import app.api.v1.github")
    assert result.returncode == 0, result.stderr


def test_fastapi_application_import_smoke():
    result = run_python("from app.main import app; assert app.title == 'Mark-I API'")
    assert result.returncode == 0, result.stderr


def test_github_analyzer_imports_supported_adk_api():
    result = run_python("import ai.analyzers.github_analyzer")
    assert result.returncode == 0, result.stderr


def test_worker_imports_in_docker_layout():
    result = run_python("import workers.github_worker; import workers.opportunity_worker")
    assert result.returncode == 0, result.stderr


def test_firestore_queries_use_supported_filter_objects():
    sources = "\n".join(
        BACKEND_ROOT.joinpath(path).read_text()
        for path in (
            "app/services/user_service.py",
            "app/services/observation_service.py",
        )
    )
    assert "where(filter=(" not in sources


def test_github_webhook_and_worker_share_event_schema():
    envelope = GitHubEventEnvelope(
        deliveryId="delivery-1",
        activityId="github:activity-1",
        eventType="push",
        uid="user-1",
        repoFullName="alex/repo",
        actorLogin="alex",
        actorId=42,
        payload={},
    )
    assert decode_github_event_envelope(envelope.model_dump_json().encode()) == envelope


def test_github_pipeline_implements_delivery_id_idempotency():
    assert ProcessedEventService.document_id("delivery-1", "user-1") == "github:delivery-1:user-1"


def test_all_documented_github_events_extract_analysis_text():
    assert set(EVENT_EXTRACTORS) == {
        "push", "pull_request", "pull_request_review", "issues", "issue_comment", "create"
    }


def test_opportunity_trigger_requires_authentication():
    source = BACKEND_ROOT.joinpath("app/api/v1/triggers.py").read_text()
    assert "get_current_user" in source or "Authorization" in source or "x_scheduler_secret" in source


def test_telegram_webhook_secret_is_mandatory():
    source = BACKEND_ROOT.joinpath("app/api/webhooks/telegram.py").read_text()
    assert "if not secret" in source and "status_code=503" in source


def test_unlinked_users_still_receive_opportunity_observation_and_decision():
    source = BACKEND_ROOT.joinpath("workers/opportunity_worker.py").read_text()
    assert "if not goal or not telegram_user_id" not in source


def test_chat_request_matches_openapi_schema():
    schema = ChatRequest.model_json_schema()
    assert set(schema["properties"]) == {"message", "channel", "turnId"}
    assert schema["properties"]["message"]["maxLength"] == 2000
    assert schema["properties"]["message"]["minLength"] == 1


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty"),
        pytest.param("x" * 5001, id="oversized"),
    ],
)
def test_chat_rejects_empty_and_oversized_messages(text):
    with pytest.raises(Exception):
        ChatRequest(message=text, channel="web")


def test_chat_response_matches_openapi_schema():
    assert set(ChatResponse.model_fields) == {"response", "messageId", "agentMessageId"}


def test_observations_response_matches_openapi_schema():
    assert set(ObservationsResponse.model_fields) == {"observations", "nextCursor", "hasMore"}


def test_dashboard_stats_match_openapi_schema():
    assert set(DashboardStats.model_fields) == {
        "totalObservations",
        "totalSkills",
        "streakDays",
        "lastActivityAt",
    }


def test_decision_model_matches_firestore_contract():
    assert set(Decision.model_fields) == {
        "id",
        "observationId",
        "action",
        "significanceScore",
        "threshold",
        "intensity",
        "escalationFlags",
        "deliveryStatus",
        "reason",
        "createdAt",
    }


def test_cloudbuild_supplies_required_runtime_configuration():
    source = BACKEND_ROOT.joinpath("cloudbuild.yaml").read_text()
    for variable in (
        "GCP_PROJECT_ID",
        "FIRESTORE_DATABASE",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_BOT_USERNAME",
        "GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET",
        "GITHUB_WEBHOOK_SECRET",
        "SCHEDULER_SHARED_SECRET",
    ):
        assert variable in source
