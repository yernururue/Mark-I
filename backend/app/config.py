from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeRole(StrEnum):
    API = "api"
    GITHUB_WORKER = "github-worker"
    OPPORTUNITY_WORKER = "opportunity-worker"


class ConfigurationError(RuntimeError):
    """Sanitised startup configuration failure."""


class Settings(BaseSettings):
    """Environment-backed configuration; required values are role-validated."""
    GCP_PROJECT_ID: str | None = None
    FIRESTORE_DATABASE: str = "mark-i"
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_BOT_USERNAME: str | None = None
    TELEGRAM_WEBHOOK_URL: str | None = None
    TELEGRAM_WEBHOOK_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_WEBHOOK_SECRET: str | None = None
    PUBSUB_GITHUB_TOPIC: str = "github-events"
    PUBSUB_OPPORTUNITY_TOPIC: str = "opportunity-collect"
    WEBHOOK_BASE_URL: str | None = None
    FRONTEND_URL: str = "http://localhost:3000"
    ENV: str = "development"

    model_config = SettingsConfigDict(
        # Look for .env in current directory and parent directory
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_for_role(self, role: RuntimeRole) -> None:
        required = {
            RuntimeRole.API: ("GCP_PROJECT_ID", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_WEBHOOK_SECRET"),
            RuntimeRole.GITHUB_WORKER: ("GCP_PROJECT_ID",),
            RuntimeRole.OPPORTUNITY_WORKER: ("GCP_PROJECT_ID",),
        }[role]
        missing = [name for name in required if not getattr(self, name)]
        if missing:
            raise ConfigurationError(f"Missing required configuration for role {role}: {', '.join(missing)}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process settings without validating them at import time."""
    return Settings()


def reset_settings_cache() -> None:
    """Test seam for isolated environment-dependent cases."""
    get_settings.cache_clear()
