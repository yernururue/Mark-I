"""
github.py — Форматы данных (схемы) для GitHub интеграции.
"""
from typing import Optional
from pydantic import BaseModel, Field


class GitHubAuthUrlResponse(BaseModel):
    authUrl: str = Field(..., description="OAuth authorization URL для редиректа")


class GitHubCallbackRequest(BaseModel):
    code: str = Field(..., description="GitHub OAuth authorization code")
    state: str = Field(..., description="Anti-CSRF state token")


class GitHubRepo(BaseModel):
    fullName: str = Field(..., description="Полное название репозитория (owner/repo)")
    private: bool = Field(..., description="Приватный ли репозиторий")
    connected: Optional[bool] = Field(None, description="Подключен ли репозиторий в Mark-I")


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
