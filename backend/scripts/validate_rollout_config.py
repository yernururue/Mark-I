#!/usr/bin/env python3
"""Validate versioned rollout inputs without reading or printing secret values."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit


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


def _https_origin(value: str) -> bool:
    """Accept an HTTPS origin that can safely enter gcloud's env-var list."""
    if not value or any(character.isspace() or character in ",\\" for character in value):
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
            and parsed.path == ""
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def validate_effective_inputs(values: dict[str, str], failures: list[str]) -> None:
    """Validate resolved build inputs; report names only, never supplied values."""
    expected = REQUIRED_SUBSTITUTIONS | {"_CONFIGURE_PUBSUB_PUSH", "PROJECT_ID"}
    for key in sorted(expected):
        if not values.get(key):
            failures.append(f"effective build input missing: {key}")

    if values.get("PROJECT_ID") != "mark-i-506218":
        failures.append("effective PROJECT_ID must match the fixed rollout project")

    tag = values.get("_IMAGE_TAG", "")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag) or tag.lower() == "latest":
        failures.append("effective _IMAGE_TAG must be an explicit release tag")

    for key in sorted(REQUIRED_SUBSTITUTIONS):
        if key.endswith("_VERSION") and not re.fullmatch(r"[1-9][0-9]*", values.get(key, "")):
            failures.append(f"effective {key} must be a positive numeric secret version")

    for key in ("_WEBHOOK_BASE_URL", "_FRONTEND_URL"):
        if not _https_origin(values.get(key, "")):
            failures.append(f"effective {key} must be an HTTPS origin without a trailing slash")

    if values.get("_TELEGRAM_WEBHOOK_URL") != values.get("_WEBHOOK_BASE_URL", "") + "/api/v1/webhooks/telegram":
        failures.append("effective _TELEGRAM_WEBHOOK_URL must use the API origin and Telegram webhook path")

    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", values.get("_TELEGRAM_BOT_USERNAME", "")):
        failures.append("effective _TELEGRAM_BOT_USERNAME is invalid")

    if values.get("_PUBSUB_PUSH_SERVICE_ACCOUNT") != "mark-i-pubsub-push@mark-i-506218.iam.gserviceaccount.com":
        failures.append("effective _PUBSUB_PUSH_SERVICE_ACCOUNT must match the dedicated rollout identity")

    if values.get("_CONFIGURE_PUBSUB_PUSH") not in {"true", "false"}:
        failures.append("effective _CONFIGURE_PUBSUB_PUSH must be true or false")


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
        "post-deploy service verification": "id: 'verify-bootstrap-services'",
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

    last_deploy_position = source.find("id: 'deploy-opportunity-worker'")
    verification_position = source.find("id: 'verify-bootstrap-services'")
    push_position = source.find("id: 'configure-pubsub-push'")
    if not last_deploy_position < verification_position < push_position:
        failures.append("service verification must run after deploys and before Pub/Sub push changes")

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-effective-inputs",
        action="store_true",
        help="also validate resolved Cloud Build inputs from ROLLOUT_<input> environment variables",
    )
    options = parser.parse_args()
    failures: list[str] = []
    validate_cloudbuild(failures)
    index_count = validate_firestore_indexes(failures)
    validate_runtime(failures)
    if options.require_effective_inputs:
        keys = REQUIRED_SUBSTITUTIONS | {"_CONFIGURE_PUBSUB_PUSH", "PROJECT_ID"}
        values = {key: os.environ.get(f"ROLLOUT_{key.lstrip('_')}", "") for key in keys}
        validate_effective_inputs(values, failures)

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
