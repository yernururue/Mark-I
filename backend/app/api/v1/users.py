"""
users.py — Эндпоинты профиля. Это "двери" нашего приложения.
Здесь сервер принимает запросы из интернета (от фронтенда).
Как мы обсуждали в user_service.py, эти "двери" сами ничего не делают, 
а только вызывают сервисы (поваров).
"""

# APIRouter позволяет разбивать API на кусочки, чтобы не писать 1000 строк в одном файле.
# Depends (от слова Зависеть) — магия FastAPI. Позволяет перед выполнением кода вызвать функцию-помощника.
from fastapi import APIRouter, Depends, HTTPException

from app.api.contracts import error_responses
from app.dependencies import get_user_service
from app.errors import ConflictError
from app.middleware.auth import get_current_user
from app.models.user import CreateProfileRequest, UpdateProfileRequest, UserProfile
from app.services.user_service import UserService

# Создаем мини-приложение (роутер). Все адреса здесь будут начинаться с "/me".
router = APIRouter(prefix="/me", tags=["User"])


@router.get("", response_model=UserProfile, responses=error_responses(401, 404), operation_id="getProfile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """
    Получить данные профиля (GET /api/v1/me).
    
    Как тут работает Depends?
    Когда приходит запрос, FastAPI смотрит на аргументы.
    1. Видит Depends(get_current_user). Ага, нужно проверить токен. Идет в auth.py.
       Если токен плохой, сервер сразу выкинет ошибку 401 и даже не дойдет до строки ниже! 
       Это называется Fail-Fast (падай быстро).
    2. Видит Depends(_get_user_service). Готовит сервис для работы.
    3. Только после этого запускается код внутри функции.
    """
    # Просим сервис найти пользователя по его ID (uid мы получили из расшифрованного токена)
    profile = service.get_profile(current_user["uid"])

    # Если профиля нет (человек авторизовался через Google, но еще не заполнил данные на сайте)
    if profile is None:
        raise HTTPException(
            status_code=404, # 404 означает Not Found (Не найдено)
            detail={"error": {"code": "NOT_FOUND", "message": "Профиль не найден. Пройдите регистрацию."}},
        )

    return profile


@router.post("", response_model=UserProfile, status_code=201, responses=error_responses(401, 409, 422), operation_id="createProfile")
async def create_profile(
    request: CreateProfileRequest,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """
    Создать профиль (POST /api/v1/me).
    status_code=201 означает "Успешно создано" (обычно успешный ответ это 200).
    """
    try:
        profile = service.create_profile(
            uid=current_user["uid"],
            email=current_user["email"],
            request=request,
        )
    except ConflictError:
        raise HTTPException(
            status_code=409, # 409 означает Conflict (Конфликт) - такой ресурс уже есть
            detail={"error": {"code": "CONFLICT", "message": "Профиль уже существует."}},
        )

    return profile


@router.patch("", response_model=UserProfile, responses=error_responses(401, 404, 422), operation_id="updateProfile")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """
    Обновить профиль (PATCH /api/v1/me).
    PATCH в HTTP означает "частичное обновление" (в отличие от PUT, который перезаписывает всё).
    """
    # Убеждаемся, что пользователю есть что обновлять
    existing = service.get_profile(current_user["uid"])
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Профиль не найден."}},
        )

    # Просим сервис обновить базу
    updated = service.update_profile(
        uid=current_user["uid"],
        request=request,
    )

    return updated
