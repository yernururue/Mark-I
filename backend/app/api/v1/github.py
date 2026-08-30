"""
github.py — Эндпоинты интеграции с GitHub.
"""
from fastapi import APIRouter, Depends

from app.api.contracts import error_responses
from app.dependencies import get_github_service
from app.middleware.auth import get_current_user
from app.models.github import (
    GitHubAuthUrlResponse,
    GitHubCallbackRequest,
    GitHubCallbackResponse,
    GitHubReposResponse,
    DisconnectResponse,
    SelectReposRequest,
    SelectReposResponse,
)
from app.services.github_service import GitHubService

router = APIRouter(prefix="/github", tags=["GitHub"])





@router.get("/auth-url", response_model=GitHubAuthUrlResponse, responses=error_responses(401, 422), operation_id="getGithubAuthUrl")
async def get_github_auth_url(
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    """Получить ссылку на GitHub OAuth авторизацию (GET /api/v1/github/auth-url)."""
    auth_url = service.generate_auth_url(current_user["uid"])
    return GitHubAuthUrlResponse(authUrl=auth_url)


@router.post("/callback", response_model=GitHubCallbackResponse, responses=error_responses(400, 401, 422), operation_id="githubOAuthCallback")
async def github_oauth_callback(
    request: GitHubCallbackRequest,
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    """Обменять OAuth код на токен и получить список репозиториев (POST /api/v1/github/callback)."""
    result = await service.exchange_code(
        user_uid=current_user["uid"],
        code=request.code,
        state=request.state,
    )
    return GitHubCallbackResponse(
        githubUsername=result["githubUsername"],
        repos=result["repos"],
    )


@router.get("/repos", response_model=GitHubReposResponse, response_model_exclude_none=True, responses=error_responses(400, 401, 422), operation_id="getGithubRepos")
async def get_github_repos(
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    """Получить список доступных репозиториев пользователя (GET /api/v1/github/repos)."""
    repos = await service.list_repos(current_user["uid"])
    return GitHubReposResponse(repos=repos)


@router.post("/repos", response_model=SelectReposResponse, responses=error_responses(401, 422), operation_id="selectGithubRepos")
async def select_github_repos(
    request: SelectReposRequest,
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    """Выбрать репозитории для отслеживания и зарегистрировать вебхуки (POST /api/v1/github/repos)."""
    result = await service.select_repos(
        user_uid=current_user["uid"],
        repo_names=request.repos,
    )
    return SelectReposResponse(
        connectedRepos=result["connectedRepos"],
        webhooksRegistered=result["webhooksRegistered"],
    )


@router.delete("/disconnect", response_model=DisconnectResponse, responses=error_responses(401, 422), operation_id="disconnectGithub")
async def disconnect_github(
    current_user: dict = Depends(get_current_user),
    service: GitHubService = Depends(get_github_service),
):
    """Отключить GitHub полностью (DELETE /api/v1/github/disconnect)."""
    await service.disconnect(current_user["uid"])
    return DisconnectResponse(disconnected=True)
