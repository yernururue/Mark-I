# Фаза 1.1 — configuration lifecycle

## Цель

Ввести единый, lazy и тестируемый Settings API без import-time validation и без чтения/вывода secret values.

## Архитектурное решение

- `Settings` остаётся единственной typed моделью environment configuration.
- Единственная точка получения runtime config — cached factory `get_settings`.
- Глобальный eager instance удаляется; consumers получают settings через provider или constructor.
- Обязательные variables проверяются не при импорте, а на process startup с учётом роли: API, GitHub worker, Opportunity worker.
- Tests создают Settings из явных values с отключённым `.env` и очищают cache между cases.

## Scope работ после approval

1. Перевести Pydantic Settings на актуальный `SettingsConfigDict`/alias mechanism без deprecated `Field(..., env=...)`.
2. Определить допустимые environment names и runtime roles как закрытые typed values.
3. Разделить безопасные defaults и обязательные runtime values; secret defaults запрещены.
4. Реализовать cached accessor и deterministic cache reset seam для tests.
5. Реализовать role-specific validation, которая сообщает все отсутствующие variable names одним sanitised error.
6. Мигрировать все consumers с module-level `settings` на constructor/provider access.
7. Убрать module-level Settings creation из AI, services, workers, bot и FastAPI imports.
8. Убедиться, что `.env` используется только local runtime, а test configuration не зависит от него.

## Затрагиваемые файлы

- `app/config.py`;
- `app/main.py`;
- `app/dependencies.py`;
- `app/api/v1/github.py`;
- `app/api/webhooks/github.py`;
- `app/services/opportunity_service.py`;
- `ai/agent.py`, `ai/chat_agent.py`, `ai/analyzers/*`;
- `telegrambot/bot.py` и Telegram client construction;
- `workers/github_worker.py`, `workers/opportunity_worker.py`;
- config/startup tests и fixtures;
- `.env.example` только если environment contract требует синхронизации.

## Failure semantics

- Import никогда не завершается configuration error.
- Startup production process завершается до открытия listeners/HTTP sessions, если role-required config отсутствует.
- Error содержит environment name, runtime role и список отсутствующих keys, но не values.
- Development/test mode не превращает security-sensitive production values в неявно допустимые fake secrets.

## Tests

- два вызова accessor возвращают один instance;
- cache reset позволяет независимо тестировать разные environments;
- explicit Settings construction не читает real environment;
- каждая role принимает минимально достаточный набор и отклоняет отсутствие нужного key;
- sanitised error не содержит известного test secret value;
- import config/app/workers не создаёт Settings и external clients;
- Pydantic deprecation warnings равны нулю.

## Acceptance criteria

- Все production consumers используют один Settings contract.
- Нет module-level eager Settings instance.
- Config regression xfail заменён passing tests.
- `/health` module import не зависит от GitHub, Telegram или Gemini secrets.
- Missing production config диагностируется явно на startup boundary.

## Не входит

- Cloud Run `--set-secrets` wiring — этап 4.
- Изменение значений production secrets.
- Security policy Telegram/Scheduler endpoints.

## Rollback boundary

Один отдельный commit, включающий accessor, consumer migration и config tests. Частичное сосуществование eager и lazy contracts за пределами commit запрещено.

