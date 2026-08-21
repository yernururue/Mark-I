# Задача 7: Opportunity Discovery + Deploy

## Цель
Автоматический поиск релевантных возможностей + финальный деплой на Cloud Run.

## Что делать

1. `app/services/opportunity_service.py` — сбор из источников
2. `ai/analyzers/opportunity_analyzer.py` — Gemini relevance scoring
3. `workers/opportunity_worker.py` — Pub/Sub consumer
4. Cloud Scheduler job (hourly trigger)
5. `Dockerfile` — оптимизация
6. `cloudbuild.yaml` — CI/CD
7. Firestore Security Rules deploy

## Acceptance Criteria
- Cloud Scheduler → Pub/Sub → Worker → Gemini → Observations
- Релевантные opportunities уведомляют через Telegram
- Cloud Run deploy работает
- Security Rules блокируют прямую запись от клиента
