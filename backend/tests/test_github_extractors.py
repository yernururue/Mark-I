from __future__ import annotations

import pytest

from app.models.github import GitHubEventEnvelope
from workers.github_extractors import EVENT_EXTRACTORS, UnsupportedGitHubEvent, extract_github_event


def envelope(event_type: str, payload: dict) -> GitHubEventEnvelope:
    return GitHubEventEnvelope(
        deliveryId="delivery-1",
        activityId="github:activity-1",
        eventType=event_type,
        uid="user-1",
        repoFullName="alex/repo",
        actorLogin="alex",
        actorId=42,
        payload=payload,
    )


@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        ("push", {"ref": "refs/heads/main", "commits": [{"message": "add tests", "added": ["test.py"]}]}),
        ("pull_request", {"action": "opened", "pull_request": {"title": "Add tests", "body": "coverage", "html_url": "https://x/pr/1"}}),
        ("pull_request_review", {"action": "submitted", "review": {"state": "approved", "body": "looks good"}, "pull_request": {"title": "Add tests", "html_url": "https://x/pr/1"}}),
        ("issues", {"action": "opened", "issue": {"title": "Bug", "body": "details", "labels": [{"name": "bug"}], "html_url": "https://x/issues/1"}}),
        ("issue_comment", {"action": "created", "issue": {"title": "Bug", "html_url": "https://x/issues/1", "pull_request": {}}, "comment": {"body": "I can fix this", "html_url": "https://x/issues/1#comment"}}),
        ("create", {"ref": "feature", "ref_type": "branch", "repository": {"html_url": "https://x/repo"}}),
    ],
)
def test_each_supported_event_extracts_meaningful_context(event_type, payload):
    context = extract_github_event(envelope(event_type, payload))

    assert context.eventType == event_type
    assert context.repo == "alex/repo"
    assert context.changesText.strip()
    assert context.metadata["deliveryId"] == "delivery-1"
    assert context.metadata["repo"] == "alex/repo"


def test_registry_covers_every_webhook_event_registered_by_github_service():
    assert set(EVENT_EXTRACTORS) == {"push", "pull_request", "pull_request_review", "issues", "issue_comment", "create"}


def test_unsupported_event_has_no_fallback_extractor():
    with pytest.raises(UnsupportedGitHubEvent):
        extract_github_event(envelope("fork", {}))
