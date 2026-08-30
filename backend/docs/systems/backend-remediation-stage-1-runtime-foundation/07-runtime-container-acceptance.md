# Фаза 1.6 — runtime and container acceptance

## Цель

Доказать, что результаты фаз 1.0–1.5 работают совместно в каноническом Python 3.11 Docker runtime, а не только в локальном Python 3.14.

## Preconditions

- Все предыдущие phase gates passing.
- Docker daemon запущен локально либо эквивалентный container gate доступен в CI.
- Test-safe runtime variables определены; реальные GCP credentials и production secrets не используются.

## Scope работ после approval

1. Выполнить clean install/build из locked Python 3.11 dependency set.
2. Запустить import smoke для config, dependencies, всех routers, app и обоих workers внутри image.
3. Построить generated OpenAPI и сравнить с phase 1.0 snapshot на отсутствие незапланированного drift.
4. Запустить API container с test-safe config и проверить `/health`.
5. Доказать, что health smoke не вызывает Telegram setup, Firestore, Pub/Sub или Gemini; external adapters заменяются test-safe composition/flags.
6. Выполнить worker import/startup-check path без запуска бесконечного subscriber и без GCP network.
7. Запустить полный unit/contract suite и проверить warnings.
8. Проверить отсутствие secrets в image history, test logs и error output.
9. Сформировать stage-1 acceptance report с командами, версиями, результатами и оставшимися xfail по этапам 2–5.
10. Только после всех gates обновить task statuses и plan status по tracker lifecycle.

## Затрагиваемые файлы

- `Dockerfile`;
- dependency lock/constraints;
- startup/import smoke tests;
- CI/build config при наличии;
- stage acceptance report;
- `backend/TRACKER.yaml` после фактического выполнения.

## Acceptance matrix

| Проверка | Ожидаемый результат |
|---|---|
| Clean Python 3.11 install | Success с зафиксированными versions |
| `app.main` import | Success, no network/credentials |
| Router/OpenAPI build | Success, no unapproved schema drift |
| GitHub worker import | Success в `/app` layout |
| Opportunity worker import | Success в `/app` layout |
| TestClient health | HTTP 200 |
| Container health | HTTP 200 |
| Missing production key | Sanitised fail-fast startup error |
| Stage-1 regression tests | Passing, без stage-1 xfail |
| Other remediation tests | Остаются ожидаемыми strict xfail |
| Pydantic env warnings | 0 |

## Failure handling

- Любой container-only defect возвращается владельцу соответствующей фазы; фаза 1.6 не маскирует его workaround через `PYTHONPATH` или fake credentials.
- Если Docker daemon/CI недоступен, задача остаётся in-progress с явным blocker; этап не объявляется завершённым.
- Unexpected pass этапов 2–5 исследуется на scope creep до снятия xfail.

## Acceptance criteria

- Все пункты Definition of Done из `plan.md` подтверждены артефактами запуска.
- Container использует тот же dependency set, который прошёл tests.
- Ни один smoke test не обращается к production GCP.
- Tracker не противоречит acceptance report.

## Не входит

- Staging deploy.
- Live GCP smoke.
- GitHub/Telegram/Opportunity E2E.

## Shipping rule

Завершение этого плана означает готовность только этапа 1 remediation roadmap. Перемещение в `docs/systems/` допустимо по общим правилам проекта после выполнения всех семи задач и компиляции README; весь backend remediation при этом ещё не считается shipped.

