# Фаза 1.3 — package and runtime layout

## Цель

Сделать local, test и Docker imports идентичными и убрать все import-time runtime side effects из workers.

## Канонический layout

Docker продолжает копировать содержимое `backend/` в `/app`. Поэтому канонические packages:

- `app.*`;
- `ai.*`;
- `workers.*`;
- `telegrambot.*`.

Namespace `backend.*` внутри runtime кода запрещён.

## Scope работ после approval

1. Инвентаризировать и заменить runtime imports `backend.*` на канонические top-level imports.
2. Проверить package markers и исключить зависимость от repository root в `sys.path`.
3. Перенести Settings, Firestore и Pub/Sub client construction из module scope в worker composition roots.
4. Сделать worker callbacks тонкими adapters над injected processing services/functions.
5. Отделить import smoke от бесконечного subscriber loop.
6. Согласовать worker command/module names в Docker/Cloud Build без изменения deployment security.
7. Добавить статический regression test на запрещённые `backend.*` runtime imports.
8. Проверить local commands из `cwd=backend` и container commands из `/app`.

## Затрагиваемые файлы

- `workers/github_worker.py`;
- `workers/opportunity_worker.py`;
- `ai/agent.py`;
- `ai/analyzers/github_analyzer.py`;
- другие runtime modules, найденные import inventory;
- `Dockerfile`;
- `cloudbuild.yaml` только если module command не соответствует каноническому layout;
- worker import tests.

## Runtime invariants

- Import worker не создаёт Firestore/Pub/Sub client и не ищет ADC.
- Subscriber создаётся только внутри worker startup path.
- Callback получает зависимости из composition root.
- Import не запускает event loop и не регистрирует webhook.
- Module command остаётся пригодным для non-interactive Cloud Run process.

## Tests

- import обоих workers с очищенными credential variables;
- source scan не находит `backend.app`, `backend.ai`, `backend.workers`;
- import выполняется из temp/container-like `/app` path, а не из repository root;
- fake subscriber/client можно передать без patching module globals;
- worker main/startup validation тестируется отдельно от message processing.

## Acceptance criteria

- Один import style работает local и в Docker.
- Worker import regression xfail стал passing.
- External clients отсутствуют на module scope.
- Docker/Cloud Build module commands ссылаются на существующие canonical packages.

## Не входит

- Изменение event envelope, ack/nack, retries или idempotency.
- Cloud Run service/job architecture decision.

## Rollback boundary

Отдельный commit, после которого API и оба workers проходят import suite. Временное изменение `PYTHONPATH` не является допустимым fix.

