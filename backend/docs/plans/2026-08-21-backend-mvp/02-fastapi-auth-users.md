# Задача 2: FastAPI App + Auth + User Endpoints

## Цель
Запускаемый FastAPI сервер с Firebase Auth, health check и полным CRUD для пользователей.

## Что делать

1. `app/main.py` — FastAPI app, CORS, роутеры, health check
2. `app/middleware/auth.py` — Firebase Auth dependency (verify_id_token)
3. `app/models/*.py` — все Pydantic модели по OpenAPI spec
4. `app/services/user_service.py` — Firestore CRUD для `users/{uid}`
5. `app/api/v1/users.py` — GET/POST/PATCH /api/v1/me
6. `app/api/v1/router.py` — агрегатор v1 роутеров
7. `app/dependencies.py` — dependency injection (Firestore client и т.д.)

## Acceptance Criteria
- `uvicorn app.main:app` запускается
- GET /health возвращает 200
- POST /api/v1/me создаёт пользователя в Firestore
- GET /api/v1/me возвращает профиль
- PATCH /api/v1/me обновляет профиль
- Без токена → 401
