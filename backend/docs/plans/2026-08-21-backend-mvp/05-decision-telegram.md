# Задача 5: Decision Policy + Telegram Bot

## Цель
Детерминированная логика решений + Telegram бот для уведомлений и привязки аккаунта.

## Что делать

1. `app/services/decision_service.py` — Python код решений (if/else, НЕ промпт)
2. `app/services/telegram_service.py` — отправка через Bot API
3. `telegrambot/bot.py` — bot setup
4. `telegrambot/handlers.py` — /start, /link handlers
5. `app/api/v1/telegram.py` — link/unlink endpoints
6. `app/api/webhooks/telegram.py` — webhook handler

## Acceptance Criteria
- Decision policy: chill=7, normal=5, brutal=3 thresholds
- Escalation rules работают (repeated_error, skill_regression, etc.)
- /start → welcome message
- /link CODE → привязка telegramUserId к uid
- Уведомления приходят в Telegram при значимых событиях
