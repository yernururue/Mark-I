# Задача 1: Инициализация проекта

## Цель
Создать файловую структуру бекенда, requirements.txt, Dockerfile и конфигурацию.

## Что делать

1. Создать все пакеты (папки с `__init__.py`):
   - `app/`, `app/api/`, `app/api/v1/`, `app/api/webhooks/`
   - `app/services/`, `app/models/`, `app/middleware/`
   - `ai/`, `ai/tools/`, `ai/analyzers/`
   - `telegrambot/`
   - `workers/`

2. `requirements.txt`:
   ```
   fastapi>=0.104.0
   uvicorn[standard]>=0.24.0
   firebase-admin>=6.2.0
   google-cloud-pubsub>=2.18.0
   google-cloud-secret-manager>=2.16.0
   google-adk>=0.3.0
   google-cloud-aiplatform>=1.38.0
   python-telegram-bot>=20.7
   httpx>=0.25.0
   pydantic>=2.5.0
   pydantic-settings>=2.1.0
   python-dotenv>=1.0.0
   ```

3. `Dockerfile` — multi-stage build для Cloud Run

4. `.env.example` — шаблон переменных окружения

5. `app/config.py` — Pydantic Settings

## Acceptance Criteria
- `pip install -r requirements.txt` работает
- `docker build .` собирается
- Структура папок соответствует TRD
