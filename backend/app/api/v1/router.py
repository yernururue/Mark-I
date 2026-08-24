"""
router.py — Сборщик всех маршрутов первой версии API (v1).

Зачем нужно версионирование (v1)?
Представьте, что через полгода вы решили полностью переделать формат профиля пользователя.
Если вы просто поменяете код, фронтенд у всех пользователей сломается, 
потому что он ожидает старый формат.
Поэтому вы создаете `/api/v2/me` для нового приложения, а старое продолжает работать на `/api/v1/me`.
"""

from fastapi import APIRouter

# Забираем мини-роутер пользователей, который мы сделали в users.py
from app.api.v1.users import router as users_router
from app.api.v1.github import router as github_router
from app.api.v1.skills import router as skills_router
from app.api.v1.observations import router as observations_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.telegram import router as telegram_router

# Создаем главный роутер для текущей версии (v1)
api_v1_router = APIRouter(prefix="/api/v1")

# Приклеиваем к нему роутер пользователей и github.
api_v1_router.include_router(users_router)
api_v1_router.include_router(github_router)
api_v1_router.include_router(skills_router)
api_v1_router.include_router(observations_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(telegram_router)
