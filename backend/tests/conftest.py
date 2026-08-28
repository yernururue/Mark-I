"""Test-only configuration that never talks to real Google services."""

from __future__ import annotations

import os


_TEST_ENV = {
    "GCP_PROJECT_ID": "mark-i-test",
    "FIRESTORE_DATABASE": "mark-i-test",
    "GEMINI_MODEL": "gemini-test",
    "TELEGRAM_BOT_TOKEN": "telegram-test-token",
    "TELEGRAM_BOT_USERNAME": "mark_i_test_bot",
    "GITHUB_CLIENT_ID": "github-test-client",
    "GITHUB_CLIENT_SECRET": "github-test-secret",
    "GITHUB_WEBHOOK_SECRET": "github-test-webhook-secret",
    "FRONTEND_URL": "http://localhost:3000",
}

for _name, _value in _TEST_ENV.items():
    os.environ[_name] = _value

