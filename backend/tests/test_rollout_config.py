"""Regression checks for effective manual Cloud Build substitutions."""

from __future__ import annotations

import pytest

from scripts.validate_rollout_config import REQUIRED_SUBSTITUTIONS, validate_effective_inputs


def valid_inputs() -> dict[str, str]:
    values = {key: "1" for key in REQUIRED_SUBSTITUTIONS if key.endswith("_VERSION")}
    values.update({
        "PROJECT_ID": "mark-i-506218",
        "_IMAGE_TAG": "release-20260906-fb9bc8d",
        "_WEBHOOK_BASE_URL": "https://mark-i-api-691051892786.us-central1.run.app",
        "_TELEGRAM_WEBHOOK_URL": "https://mark-i-api-691051892786.us-central1.run.app/api/v1/webhooks/telegram",
        "_FRONTEND_URL": "https://mark-i-506218.web.app",
        "_TELEGRAM_BOT_USERNAME": "mark1_dev_bot",
        "_PUBSUB_PUSH_SERVICE_ACCOUNT": "mark-i-pubsub-push@mark-i-506218.iam.gserviceaccount.com",
        "_CONFIGURE_PUBSUB_PUSH": "false",
    })
    return values


def test_resolved_rollout_inputs_pass():
    failures: list[str] = []
    validate_effective_inputs(valid_inputs(), failures)
    assert failures == []


@pytest.mark.parametrize("key,value", [
    ("PROJECT_ID", "unrelated-project"),
    ("_IMAGE_TAG", "latest"),
    ("_IMAGE_TAG", "$BUILD_ID"),
    ("_IMAGE_TAG", "bad/tag"),
    ("_TELEGRAM_BOT_TOKEN_VERSION", "latest"),
    ("_GITHUB_CLIENT_SECRET_VERSION", "0"),
    ("_GITHUB_WEBHOOK_SECRET_VERSION", "1,ENV=development"),
    ("_FRONTEND_URL", "http://example.com"),
    ("_FRONTEND_URL", "https://user:password@example.com"),
    ("_FRONTEND_URL", "https://example.com,ENV=development"),
    ("_FRONTEND_URL", "https://example.com/path"),
    ("_FRONTEND_URL", "https://example.com/"),
    ("_FRONTEND_URL", "https://example.com:invalid"),
    ("_FRONTEND_URL", "https://example.com\n"),
    ("_TELEGRAM_WEBHOOK_URL", "https://another.example/api/v1/webhooks/telegram"),
    ("_TELEGRAM_BOT_USERNAME", "@mark1_dev_bot"),
    ("_PUBSUB_PUSH_SERVICE_ACCOUNT", "someone@example.com"),
    ("_CONFIGURE_PUBSUB_PUSH", "TRUE"),
])
def test_bad_override_fails_without_echoing_value(key: str, value: str):
    values = valid_inputs()
    values[key] = value
    failures: list[str] = []
    validate_effective_inputs(values, failures)
    assert failures
    assert value not in "\n".join(failures)


@pytest.mark.parametrize("key", sorted(REQUIRED_SUBSTITUTIONS | {"PROJECT_ID", "_CONFIGURE_PUBSUB_PUSH"}))
def test_missing_resolved_input_fails(key: str):
    values = valid_inputs()
    del values[key]
    failures: list[str] = []
    validate_effective_inputs(values, failures)
    assert f"effective build input missing: {key}" in failures
