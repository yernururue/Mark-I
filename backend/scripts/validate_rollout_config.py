#!/usr/bin/env python3
"""Validate versioned rollout inputs without reading or printing secret values."""

from __future__ import annotations

import json
import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SUBSTITUTIONS = {
    "_IMAGE_TAG",
    "_WEBHOOK_BASE_URL",
    "_TELEGRAM_BOT_USERNAME",
    "_TELEGRAM_WEBHOOK_URL",
    "_FRONTEND_URL",
    "_PUBSUB_PUSH_SERVICE_ACCOUNT",
    "_TELEGRAM_BOT_TOKEN_VERSION",
    "_TELEGRAM_WEBHOOK_SECRET_VERSION",
    "_GITHUB_CLIENT_ID_VERSION",
    "_GITHUB_CLIENT_SECRET_VERSION",
    "_GITHUB_WEBHOOK_SECRET_VERSION",
    "_SCHEDULER_SHARED_SECRET_VERSION",
}

REQUIRED_SECRETS = {
    "mark-i-telegram-bot-token",
    "mark-i-telegram-webhook-secret",
    "mark-i-github-client-id",
    "mark-i-github-client-secret",
    "mark-i-github-webhook-secret",
    "mark-i-scheduler-shared-secret",
}

REQUIRED_RUNTIME_IDENTITIES = {
    "mark-i-api-runtime@$PROJECT_ID.iam.gserviceaccount.com",
    "mark-i-github-worker-runtime@$PROJECT_ID.iam.gserviceaccount.com",
    "mark-i-opportunity-worker-runtime@$PROJECT_ID.iam.gserviceaccount.com",
}


def validate_cloudbuild(failures: list[str]) -> None:
    source = BACKEND_ROOT.joinpath("cloudbuild.yaml").read_text(encoding="utf-8")
    substitutions = set(re.findall(r"^  (_[A-Z0-9_]+):", source, flags=re.MULTILINE))

    missing_substitutions = sorted(REQUIRED_SUBSTITUTIONS - substitutions)
    if missing_substitutions:
        failures.append(f"cloudbuild substitutions missing: {', '.join(missing_substitutions)}")

    for secret in sorted(REQUIRED_SECRETS):
        if secret not in source:
            failures.append(f"cloudbuild secret binding missing: {secret}")

    for identity in sorted(REQUIRED_RUNTIME_IDENTITIES):
        if identity not in source:
            failures.append(f"cloudbuild runtime identity missing: {identity}")

    required_fragments = {
        "regional Artifact Registry image": "us-central1-docker.pkg.dev/$PROJECT_ID/mark-i-backend/mark-i-backend:${_IMAGE_TAG}",
        "Cloud Logging-only build output": "logging: CLOUD_LOGGING_ONLY",
        "manual-build dynamic substitutions": "dynamicSubstitutions: true",
        "in-build rollout preflight": "id: 'validate-rollout-config'",
        "bootstrap push safety gate": "_CONFIGURE_PUBSUB_PUSH: 'false'",
        "Vertex AI runtime mode": "GOOGLE_GENAI_USE_VERTEXAI=true",
        "production frontend origin": "FRONTEND_URL=${_FRONTEND_URL}",
    }
    for description, fragment in required_fragments.items():
        if fragment not in source:
            failures.append(f"cloudbuild invariant missing: {description}")

    preflight_position = source.find("id: 'validate-rollout-config'")
    build_position = source.find("id: 'build-image'")
    if preflight_position < 0 or build_position < 0 or preflight_position > build_position:
        failures.append("rollout preflight must run before the container build")

    if "gcr.io/$PROJECT_ID/mark-i-backend:" in source:
        failures.append("legacy Container Registry image target is still present")
    if ":latest" in source:
        failures.append("Cloud Run secret bindings must use explicit versions, not latest")

    runtime_limits = {
        "CPU": ("      - '--cpu'\n      - '1'", 3),
        "memory": ("      - '--memory'\n      - '512Mi'", 3),
        "request timeout": ("      - '--timeout'\n      - '300s'", 3),
        "concurrency": ("      - '--concurrency'\n      - '80'", 3),
        "minimum instances": ("      - '--min'\n      - '0'", 3),
        "maximum instances": ("      - '--max'\n      - '5'", 3),
    }
    for description, (fragment, expected_count) in runtime_limits.items():
        if source.count(fragment) != expected_count:
            failures.append(
                f"Cloud Run {description} limit must be explicit on all {expected_count} services"
            )


def validate_firestore_indexes(failures: list[str]) -> int:
    document = json.loads(BACKEND_ROOT.joinpath("firestore.indexes.json").read_text(encoding="utf-8"))
    indexes = document.get("indexes")
    if not isinstance(indexes, list) or not indexes:
        failures.append("firestore.indexes.json has no composite indexes")
        return 0

    signatures: set[tuple[object, ...]] = set()
    for index in indexes:
        fields = index.get("fields", [])
        signature = (
            index.get("collectionGroup"),
            index.get("queryScope"),
            tuple((field.get("fieldPath"), field.get("order"), field.get("arrayConfig")) for field in fields),
        )
        if signature in signatures:
            failures.append(f"duplicate Firestore composite index: {index.get('collectionGroup', '<unknown>')}")
        signatures.add(signature)
    return len(indexes)


def validate_runtime(failures: list[str]) -> None:
    dockerfile = BACKEND_ROOT.joinpath("Dockerfile").read_text(encoding="utf-8")
    if dockerfile.count("FROM python:3.11-slim") < 2:
        failures.append("Dockerfile builder/runtime stages are not both pinned to Python 3.11 slim")


def main() -> int:
    failures: list[str] = []
    validate_cloudbuild(failures)
    index_count = validate_firestore_indexes(failures)
    validate_runtime(failures)

    if failures:
        for failure in failures:
            print(f"rollout-config: FAIL: {failure}")
        return 1

    print(
        "rollout-config: ok "
        f"({len(REQUIRED_SUBSTITUTIONS)} substitutions, "
        f"{len(REQUIRED_SECRETS)} secret bindings, "
        f"{len(REQUIRED_RUNTIME_IDENTITIES)} runtime identities, "
        f"{index_count} Firestore indexes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
