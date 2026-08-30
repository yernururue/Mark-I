"""
github.py — Форматы данных (схемы) для GitHub интеграции.
"""
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_validator


class GitHubAuthUrlResponse(BaseModel):
    authUrl: AnyUrl = Field(..., description="OAuth authorization URL для редиректа")


class GitHubCallbackRequest(BaseModel):
    code: str = Field(..., description="GitHub OAuth authorization code")
    state: str = Field(..., description="Anti-CSRF state token")


class GitHubRepo(BaseModel):
    fullName: str = Field(..., description="Полное название репозитория (owner/repo)")
    private: bool = Field(..., description="Приватный ли репозиторий")
    connected: bool = Field(None, description="Подключен ли репозиторий в Mark-I")


class GitHubCallbackResponse(BaseModel):
    githubUsername: str = Field(..., description="Имя пользователя GitHub")
    repos: list[GitHubRepo] = Field(..., description="Список доступных репозиториев")


class GitHubReposResponse(BaseModel):
    repos: list[GitHubRepo] = Field(..., description="Список доступных репозиториев")


class SelectReposRequest(BaseModel):
    repos: list[str] = Field(..., description="Список full_name репозиториев для отслеживания")


class SelectReposResponse(BaseModel):
    connectedRepos: list[str] = Field(..., description="Список подключенных репозиториев")
    webhooksRegistered: int = Field(..., description="Количество успешно зарегистрированных вебхуков")


class DisconnectResponse(BaseModel):
    disconnected: bool


class GitHubEventEnvelope(BaseModel):
    """Canonical versioned Pub/Sub payload shared by publisher and worker."""

    model_config = ConfigDict(extra="forbid")

    schemaVersion: Literal[2] = 2
    deliveryId: str = Field(min_length=1)
    activityId: str = Field(min_length=1)
    eventType: str = Field(min_length=1)
    eventAction: str | None = None
    uid: str = Field(min_length=1)
    repoFullName: str = Field(min_length=1)
    actorLogin: str = Field(min_length=1)
    actorId: int | None = Field(default=None, ge=1)
    payload: dict[str, Any]
    receivedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("deliveryId", "activityId", "eventType", "uid", "repoFullName", "actorLogin")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("eventAction")
    @classmethod
    def strip_optional_action(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("receivedAt")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("receivedAt must be timezone-aware")
        return value


class GitHubEventContext(BaseModel):
    """Meaningful, payload-safe input passed from a webhook extractor to AI."""

    model_config = ConfigDict(extra="forbid")

    repo: str = Field(min_length=1)
    eventType: str = Field(min_length=1)
    ref: str | None = None
    title: str | None = None
    description: str | None = None
    changesText: str = Field(min_length=1)
    metadata: dict[str, Any]
