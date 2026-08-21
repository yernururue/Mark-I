# Задача 4: AI Анализ + Observations + Skills

## Цель
GitHub события анализируются Gemini, создаются observations, обновляются skill scores.

## Что делать

1. `ai/agent.py` — ADK Agent definition
2. `ai/prompts.py` — системные промпты
3. `ai/analyzers/github_analyzer.py` — анализ push/PR через Gemini
4. `app/services/observation_service.py` — CRUD observations в Firestore
5. `app/services/skill_service.py` — обновление skills (weighted average formula)
6. `workers/github_worker.py` — Pub/Sub consumer: load context → analyze → observe → update skills
7. `app/api/v1/skills.py` — GET /api/v1/skills
8. `app/api/v1/observations.py` — GET /api/v1/observations
9. `app/api/v1/dashboard.py` — GET /api/v1/dashboard

## Acceptance Criteria
- Push event → Gemini анализирует → observation создаётся
- Skill scores обновляются по формуле: new = old * 0.7 + assessment * 0.3
- Dashboard endpoint возвращает агрегированные данные
