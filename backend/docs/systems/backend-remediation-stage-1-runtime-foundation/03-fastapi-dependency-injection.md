# Фаза 1.2 — FastAPI dependency injection

## Цель

Собрать полный FastAPI router graph через единый dependency contract и сделать database, auth и services заменяемыми в tests.

## Архитектурное решение

- `get_current_user` остаётся проверяющей Firebase dependency и возвращает claims.
- `get_current_user_id` зависит от неё и возвращает только UID.
- `get_db` является каноническим FastAPI provider Firestore client.
- Каждый router получает service через factory dependency; ручное создание service и прямые Firestore queries из routes удаляются в пределах затронутого flow.
- Shared process resources создаются один раз и закрываются lifespan hooks.

## Scope работ после approval

1. Ввести канонические database/auth dependencies с точными return types.
2. Исправить `_get_github_service` на поддерживаемую factory без локальных дубликатов.
3. Создать service factories для User, GitHub, Chat, Dashboard, Skill, Observation, Telegram и Opportunity trigger flows.
4. Передавать Settings и external clients через dependencies, а не module globals.
5. Убрать direct Firestore access из chat/dashboard routes, не меняя public response schema.
6. Сохранить один ownership point для Firebase initialization и один для Firestore client.
7. Обеспечить deterministic cleanup HTTP clients в lifespan.
8. Проверить каждый router отдельно до сборки общего `api_v1_router`.

## Затрагиваемые файлы

- `app/dependencies.py`;
- `app/middleware/auth.py`;
- `app/main.py`;
- `app/api/v1/*.py`;
- `app/api/webhooks/*.py`;
- соответствующие service methods, если route сейчас обращается к Firestore напрямую;
- dependency/import/OpenAPI tests.

## Auth invariants

- Protected endpoint всегда проходит Firebase token verification.
- UID берётся только из verified token claims, не из request body/query.
- Missing UID в claims является authentication failure, а не пустой строкой.
- Webhook/triggers auth policy не меняется в этой фазе и остаётся задачей этапа 4.

## Tests

- import каждого `app.api.v1.*` и webhook module;
- import общего router;
- generated OpenAPI без ADC/network;
- dependency override fake DB и fake current user;
- auth adapter success, missing UID и propagated verification failure;
- factory identity/lifecycle для process-scoped clients;
- route smoke tests доказывают отсутствие ручного real client construction.

## Acceptance criteria

- `get_db`, `get_current_user_id` и все используемые service factories существуют и типизированы.
- GitHub routes больше не ссылаются на `_get_github_service`.
- FastAPI dependency overrides изолируют все Google services.
- Router import и OpenAPI regression xfail стали passing.
- Public API schema не изменилась относительно phase 1.0 snapshot.

## Не входит

- Исправление public Chat/Observation/Dashboard schemas.
- Event pipeline semantics.
- Реорганизация Firestore schema.

## Rollback boundary

Один commit для provider layer и небольшие commits по router family. После каждого router commit общий OpenAPI graph должен строиться.

