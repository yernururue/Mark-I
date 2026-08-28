"""Typed, payload-safe extractors for GitHub webhook events."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.models.github import GitHubEventContext, GitHubEventEnvelope


class UnsupportedGitHubEvent(ValueError):
    """A delivery was valid but is not subscribed/supported for analysis."""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _repo(envelope: GitHubEventEnvelope) -> str:
    return envelope.repoFullName


def _metadata(envelope: GitHubEventEnvelope, **values: Any) -> dict[str, Any]:
    return {
        "deliveryId": envelope.deliveryId,
        "repo": envelope.repoFullName,
        "event": envelope.eventType,
        **{key: value for key, value in values.items() if value not in (None, "", [], {})},
    }


def extract_push(envelope: GitHubEventEnvelope) -> GitHubEventContext:
    payload = envelope.payload
    commits = payload.get("commits") or []
    parts = [f"Push to {_text(payload.get('ref')) or 'repository'}"]
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        parts.append(
            "\n".join(
                filter(
                    None,
                    [
                        f"Commit: {_text(commit.get('message'))}",
                        f"Added: {', '.join(commit.get('added') or [])}",
                        f"Modified: {', '.join(commit.get('modified') or [])}",
                        f"Removed: {', '.join(commit.get('removed') or [])}",
                    ],
                )
            )
        )
    return GitHubEventContext(
        repo=_repo(envelope), eventType=envelope.eventType, ref=_text(payload.get("ref")) or None,
        changesText="\n\n".join(parts),
        metadata=_metadata(envelope, commitCount=len(commits), sourceUrl=payload.get("compare")),
    )


def extract_pull_request(envelope: GitHubEventEnvelope) -> GitHubEventContext:
    payload = envelope.payload
    pr = payload.get("pull_request") or {}
    title, body = _text(pr.get("title")), _text(pr.get("body"))
    return GitHubEventContext(
        repo=_repo(envelope), eventType=envelope.eventType,
        ref=_text((pr.get("head") or {}).get("ref")) or None, title=title or None, description=body or None,
        changesText=f"Pull request action: {_text(payload.get('action')) or 'updated'}\nTitle: {title}\nBody: {body}",
        metadata=_metadata(envelope, action=_text(payload.get("action")), sourceUrl=pr.get("html_url"), state=pr.get("state")),
    )


def extract_pull_request_review(envelope: GitHubEventEnvelope) -> GitHubEventContext:
    payload = envelope.payload
    review, pr = payload.get("review") or {}, payload.get("pull_request") or {}
    title, body = _text(pr.get("title")), _text(review.get("body"))
    return GitHubEventContext(
        repo=_repo(envelope), eventType=envelope.eventType, title=title or None, description=body or None,
        changesText=f"Pull request review action: {_text(payload.get('action')) or 'submitted'}\nReview state: {_text(review.get('state'))}\nPR: {title}\nReview: {body}",
        metadata=_metadata(envelope, action=_text(payload.get("action")), reviewState=_text(review.get("state")), sourceUrl=pr.get("html_url")),
    )


def extract_issue(envelope: GitHubEventEnvelope) -> GitHubEventContext:
    payload = envelope.payload
    issue = payload.get("issue") or {}
    title, body = _text(issue.get("title")), _text(issue.get("body"))
    labels = [label.get("name") for label in issue.get("labels", []) if isinstance(label, dict) and _text(label.get("name"))]
    return GitHubEventContext(
        repo=_repo(envelope), eventType=envelope.eventType, title=title or None, description=body or None,
        changesText=f"Issue action: {_text(payload.get('action')) or 'updated'}\nTitle: {title}\nLabels: {', '.join(labels)}\nBody: {body}",
        metadata=_metadata(envelope, action=_text(payload.get("action")), labels=labels, sourceUrl=issue.get("html_url")),
    )


def extract_issue_comment(envelope: GitHubEventEnvelope) -> GitHubEventContext:
    payload = envelope.payload
    issue, comment = payload.get("issue") or {}, payload.get("comment") or {}
    title, body = _text(issue.get("title")), _text(comment.get("body"))
    kind = "pull request" if issue.get("pull_request") else "issue"
    return GitHubEventContext(
        repo=_repo(envelope), eventType=envelope.eventType, title=title or None, description=body or None,
        changesText=f"{kind.title()} comment action: {_text(payload.get('action')) or 'created'}\n{kind.title()}: {title}\nComment: {body}",
        metadata=_metadata(envelope, action=_text(payload.get("action")), subjectType=kind, sourceUrl=comment.get("html_url") or issue.get("html_url")),
    )


def extract_create(envelope: GitHubEventEnvelope) -> GitHubEventContext:
    payload = envelope.payload
    ref, ref_type = _text(payload.get("ref")), _text(payload.get("ref_type"))
    return GitHubEventContext(
        repo=_repo(envelope), eventType=envelope.eventType, ref=ref or None,
        changesText=f"Created {ref_type or 'reference'}: {ref or 'repository initialization'}",
        metadata=_metadata(envelope, refType=ref_type, ref=ref, sourceUrl=payload.get("repository", {}).get("html_url")),
    )


EVENT_EXTRACTORS: dict[str, Callable[[GitHubEventEnvelope], GitHubEventContext]] = {
    "push": extract_push,
    "pull_request": extract_pull_request,
    "pull_request_review": extract_pull_request_review,
    "issues": extract_issue,
    "issue_comment": extract_issue_comment,
    "create": extract_create,
}


def extract_github_event(envelope: GitHubEventEnvelope) -> GitHubEventContext:
    try:
        extractor = EVENT_EXTRACTORS[envelope.eventType]
    except KeyError as exc:
        raise UnsupportedGitHubEvent(envelope.eventType) from exc
    return extractor(envelope)
