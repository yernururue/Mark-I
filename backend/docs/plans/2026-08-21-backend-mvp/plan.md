# Backend MVP — Plan

> **Status:** planned
> **Created:** 2026-08-21
> **Author:** Yernur (backend agent)

---

## Обзор

Полная реализация бекенда Mark-I — AI-powered developer growth agent.

**Ответственность бекенда:**
- FastAPI REST API (все эндпоинты из openapi.yaml)
- Firebase Auth — проверка токенов (middleware)
- Firestore — все CRUD операции (backend единственный кто пишет!)
- GitHub Integration — OAuth, webhooks, анализ активности
- Telegram Bot — /start, /link, уведомления, чат
- ADK Agent + Gemini — анализ кода, чат, оценка релевантности
- Decision Policy — детерминированная логика уведомлений
- Pub/Sub Workers — async обработка событий
- Opportunity Discovery — сбор и оценка контента
- Cloud Run — деплой и инфраструктура

**НЕ трогаем (ответственность фронтенда):**
- `frontend/` — вообще ничего
- Firebase Auth client-side flow
- UI/UX, дашборд, чат-виджет
- Firebase Hosting

---

## Контракт с фронтендом

Фронтенд получает от нас:
1. REST API по `/api/v1/*` (Bearer token auth)
2. Firestore схема для realtime listeners (read-only)
3. OpenAPI спецификация (`openapi.yaml`)

Точки синхронизации:
- `openapi.yaml` — формальный API контракт
- `docs/FIRESTORE.md` — схема базы данных
- `docs/API.md` — человекочитаемая API документация

---

## Фазы

### Фаза 1: Фундамент
- FastAPI приложение, конфиг, CORS
- Firebase Auth middleware
- Pydantic модели (по OpenAPI)
- User Service + эндпоинты (/me)
- Health check
- requirements.txt, Dockerfile

### Фаза 2: GitHub интеграция
- GitHub OAuth flow (auth-url, callback)
- Secret Manager для токенов
- Webhook receiver + HMAC валидация
- Repo selection + webhook registration
- Pub/Sub publishing

### Фаза 3: AI + Анализ
- ADK Agent setup
- GitHub Analyzer (Gemini)
- Observation Service
- Skill Service (weighted average)
- GitHub Worker (Pub/Sub consumer)
- Dashboard endpoint

### Фаза 4: Decision Policy + Telegram
- Decision Service (deterministic Python)
- Telegram Bot (/start, /link)
- Telegram Service (отправка уведомлений)
- Telegram webhook handler
- Telegram link/unlink API

### Фаза 5: Unified Chat
- Chat Service (web + telegram → одна логика)
- ADK Agent tools (read_profile, read_skills, etc.)
- Chat API endpoints
- Messages API endpoints

### Фаза 6: Opportunities + Deploy
- Opportunity Service + Worker
- Cloud Scheduler config
- Final Cloud Run deploy
- Firestore Security Rules

---

## Зависимости

```
Фаза 1 ──→ Фаза 2 ──→ Фаза 3 ──→ Фаза 4 ──→ Фаза 5
                                      │
                                      └──→ Фаза 6
```

---

## Архитектура

См. `diagram.excalidraw` в этой же папке.
