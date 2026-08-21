# Задача 6: Unified Chat

## Цель
Единый чат через веб и Telegram — один ADK Agent, одна история.

## Что делать

1. `app/services/chat_service.py` — единая точка входа для обоих каналов
2. `ai/tools/*.py` — все tools для агента
3. `app/api/v1/chat.py` — POST /api/v1/chat, GET /api/v1/messages
4. Интеграция Telegram messages → тот же chat_service

## Acceptance Criteria
- POST /api/v1/chat → agent response с контекстом
- Telegram message → тот же agent
- Единая история в Firestore users/{uid}/messages
- Agent имеет доступ к tools (read_profile, read_skills, etc.)
