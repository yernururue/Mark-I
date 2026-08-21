# Задача 3: GitHub Integration

## Цель
Пользователь подключает GitHub, выбирает репозитории, webhook'и регистрируются.

## Что делать

1. `app/services/github_service.py` — OAuth flow, Secret Manager, webhook management
2. `app/api/v1/github.py` — все GitHub эндпоинты
3. `app/api/webhooks/github.py` — webhook receiver (HMAC validation, Pub/Sub publish)
4. Pub/Sub publishing для async обработки

## Acceptance Criteria
- GET /api/v1/github/auth-url возвращает OAuth URL
- POST /api/v1/github/callback обменивает код на токен
- Токен сохраняется в Secret Manager (НЕ в Firestore)
- POST /api/v1/github/repos регистрирует webhooks
- Webhook events проходят HMAC валидацию
