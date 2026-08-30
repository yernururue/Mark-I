from __future__ import annotations

import asyncio

import httpx
import pytest

from app.models.github import GitHubEventEnvelope
from app.services.github_evidence_service import (
    GitHubEvidenceRetryableError,
    GitHubEvidenceService,
)


class Response:
    def __init__(self, status_code: int, data, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self._data = data
        self.headers = headers or {}

    def json(self):
        return self._data


class HTTP:
    def __init__(self, response: Response | Exception) -> None:
        self.response = response
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def envelope(event_type: str, payload: dict) -> GitHubEventEnvelope:
    return GitHubEventEnvelope(
        deliveryId="delivery-1",
        activityId="github:activity-1",
        eventType=event_type,
        eventAction=payload.get("action"),
        uid="user-1",
        repoFullName="alex/repo",
        actorLogin="alex",
        actorId=42,
        payload=payload,
    )


def collect(event: GitHubEventEnvelope, response: Response | Exception, **limits):
    http = HTTP(response)
    service = GitHubEvidenceService(http, lambda uid: "oauth-token", **limits)
    return asyncio.run(service.collect(event)), http


def test_push_fetches_compare_patches_and_redacts_secrets_and_generated_files():
    event = envelope("push", {"before": "aaa", "after": "bbb"})
    result, http = collect(
        event,
        Response(
            200,
            {
                "files": [
                    {
                        "filename": "app/service.py",
                        "patch": "@@ -1 +1 @@\n-password = 'real-secret'\n+api_key = 'also-secret'\n+def safe(): pass",
                    },
                    {"filename": "node_modules/lib.js", "patch": "+console.log('generated')"},
                    {"filename": "assets/logo.png", "patch": None},
                ]
            },
        ),
    )

    assert result.supports_proficiency is True
    assert result.file_count == 1
    assert "def safe" in result.text
    assert "real-secret" not in result.text and "also-secret" not in result.text
    assert "node_modules" not in result.text
    assert http.calls[0][0].endswith("/repos/alex/repo/compare/aaa...bbb")
    assert http.calls[0][1]["headers"]["Authorization"] == "Bearer oauth-token"


def test_pull_request_review_fetches_changed_file_patches():
    event = envelope(
        "pull_request_review",
        {"action": "submitted", "number": 17, "pull_request": {"number": 17}},
    )
    result, http = collect(
        event,
        Response(200, [{"filename": "src/api.py", "patch": "+def endpoint(): pass"}]),
    )

    assert result.supports_proficiency is True
    assert "src/api.py" in result.text
    assert http.calls[0][0].endswith("/repos/alex/repo/pulls/17/files?per_page=100")


@pytest.mark.parametrize("event_type", ["issues", "issue_comment", "create"])
def test_non_code_events_never_call_github_or_support_proficiency(event_type):
    event = envelope(event_type, {})
    result, http = collect(event, Response(500, {}))

    assert result.supports_proficiency is False
    assert result.omission_reason == "event_has_no_code_evidence"
    assert http.calls == []


def test_binary_or_unavailable_patches_do_not_support_proficiency():
    event = envelope("pull_request", {"action": "opened", "number": 2})
    result, _ = collect(event, Response(200, [{"filename": "image.png", "patch": None}]))

    assert result.supports_proficiency is False
    assert result.omission_reason == "no_usable_patch"


def test_evidence_is_bounded_and_marks_truncation():
    event = envelope("pull_request", {"action": "opened", "number": 2})
    result, _ = collect(
        event,
        Response(
            200,
            [
                {"filename": "one.py", "patch": "+" + "a" * 100},
                {"filename": "two.py", "patch": "+" + "b" * 100},
            ],
        ),
        max_files=1,
        max_bytes=80,
        max_patch_bytes=40,
    )

    assert result.supports_proficiency is True
    assert result.truncated is True
    assert len(result.text.encode("utf-8")) <= 80
    assert "two.py" not in result.text


@pytest.mark.parametrize(
    "response",
    [
        Response(429, {}),
        Response(503, {}),
        Response(403, {}, {"X-RateLimit-Remaining": "0"}),
        httpx.ReadTimeout("timeout"),
    ],
)
def test_transient_github_failures_are_retryable(response):
    event = envelope("push", {"before": "aaa", "after": "bbb"})

    with pytest.raises(GitHubEvidenceRetryableError):
        collect(event, response)


def test_terminal_github_response_skips_proficiency_without_retry_loop():
    event = envelope("push", {"before": "aaa", "after": "bbb"})
    result, _ = collect(event, Response(404, {}))

    assert result.supports_proficiency is False
    assert result.omission_reason == "github_http_404"
