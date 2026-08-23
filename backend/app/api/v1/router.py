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

# Создаем главный роутер для текущей версии (v1)
api_v1_router = APIRouter(prefix="/api/v1")

# Приклеиваем к нему роутер пользователей и github.
api_v1_router.include_router(users_router)
api_v1_router.include_router(github_router)
