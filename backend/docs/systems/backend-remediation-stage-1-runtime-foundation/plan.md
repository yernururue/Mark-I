# Этап 1 — восстановление runtime foundation backend

> **Статус:** planned — требуется явное утверждение перед реализацией
> **Создан:** 2026-08-29
> **Область:** только `backend/`
> **Источник:** `backend/docs/reports/2026-08-28-backend-remediation-roadmap.md`
> **Связанные требования:** PRD F1, F5–F12 и NFR; TRD §§4, 5, 6.3, 7, 8.2–8.3

---

## 1. Результат этапа

После этапа FastAPI API, GitHub worker и Opportunity worker должны иметь один воспроизводимый Python/Docker runtime contract. Все три entrypoint должны импортироваться без сетевых вызовов и без реальных GCP credentials, получать конфигурацию и внешние зависимости через явные composition roots и использовать поддерживаемые API Google ADK и Firestore.

Этап не доказывает корректность GitHub event pipeline или соответствие всего REST API OpenAPI. Эти работы остаются в этапах 2 и 3 remediation roadmap.

## 2. Подтверждённый baseline

Проверка от 2026-08-29 подтверждает:

- test suite: 70 passed, 26 strict xfailed, 14 Pydantic warnings;
- `app.config` не предоставляет `get_settings` и создаёт `Settings` при импорте;
- шесть routers импортируют отсутствующие `get_db` и `get_current_user_id`;
- GitHub router использует неопределённую `_get_github_service`;
- workers используют `backend.*`, хотя Docker копирует `backend/` как содержимое `/app`;
- workers и AI modules создают settings/GCP clients на уровне модулей;
- GitHub analyzer импортирует отсутствующий `google.antigravity`;
- локально установлены Google ADK 2.7.1, Firestore 2.28.1, Pydantic 2.13.4 и FastAPI 0.141.1;
- `requirements.txt` задаёт только минимальные версии и не гарантирует повторяемый Docker build;
- Firestore services используют неподдерживаемые tuple filters и client-level transactional decorator;
- Docker CLI 29.5.2 доступен, но локальный Docker daemon сейчас не запущен.

Python 3.14 local environment используется только для быстрой диагностики. Каноническим runtime этапа остаётся Python 3.11 из Dockerfile, как требует TRD.

## 3. Анализ roadmap и принятые уточнения

Пять фаз 1.1–1.5 в roadmap корректно описывают основные дефекты, но для безопасного исполнения добавляются две контрольные фазы:

1. **Фаза 1.0 — baseline и freeze.** Не позволяет смешать runtime remediation с будущими API/product изменениями и фиксирует версии зависимостей.
2. **Фаза 1.6 — integrated acceptance.** Не позволяет объявить этап готовым только по unit tests без проверки реального Docker layout.

Дополнительные архитектурные уточнения:

- импорт Python-модуля не должен читать секреты, создавать GCP clients, открывать HTTP sessions или выполнять network I/O;
- конфигурация валидируется по роли процесса: API, GitHub worker или Opportunity worker;
- module-level compatibility alias `settings` не сохраняется, если он снова создаёт import-time side effect;
- `app`, `ai`, `workers`, `telegrambot` являются каноническими top-level packages внутри `/app`;
- Google ADK используется через внутренний adapter; business code не зависит от Runner/Event internals SDK;
- Firestore tests проверяют production API shape, а не обучают fake несуществующим методам;
- strict `xfail` удаляется только одновременно с исправлением и положительным regression test.

## 4. Scope

### Входит

- конфигурационный lifecycle и startup validation;
- FastAPI dependency graph и test overrides;
- package/import layout API и обоих workers;
- поддерживаемый Google ADK adapter для GitHub analysis;
- разделение proficiency assessment и notification significance в AI output contract;
- Firestore FieldFilter, transactions и service input invariants;
- dependency reproducibility для Python 3.11;
- unit, import, TestClient и Docker smoke gates;
- перевод относящихся к этапу 1 strict xfail tests в passing tests.

### Не входит

- единый GitHub Pub/Sub envelope, user resolution и idempotency — этап 2;
- extractors всех GitHub event types и полная escalation semantics — этап 2;
- изменение public REST schemas, pagination, Dashboard/Decision contracts — этап 3;
- Scheduler/Telegram hardening и Cloud Run secret wiring — этап 4;
- opportunity semantics, performance и настоящий staging E2E — этап 5;
- любые изменения в `frontend/`.

Если для выполнения этапа потребуется изменить `openapi.yaml`, `docs/FIRESTORE.md` или другие shared contracts, работа останавливается и выносится на отдельное согласование: этап 1 не должен незаметно менять внешний контракт.

## 5. Целевая архитектура

Каждый process entrypoint является composition root:

1. entrypoint получает cached `Settings`;
2. entrypoint выполняет validation для своей runtime role;
3. providers создают Firestore, HTTP, Pub/Sub, Secret Manager и AI adapters;
4. routers/workers получают готовые services через dependency injection;
5. services зависят от typed ports и доменных моделей, а не от глобальных SDK objects;
6. shutdown lifecycle закрывает созданные process-scoped resources.

Архитектурная схема находится в `diagram.excalidraw`, зависимости и blockers — в `blockers.excalidraw`.

## 6. Архитектурные решения этапа

| Область | Решение | Причина |
|---|---|---|
| Settings | Единственный lazy cached factory; явный cache reset в tests | Нет import-time validation и детерминированные overrides |
| Validation | Проверка обязательных variables по runtime role | API и workers не требуют лишние секреты; ошибки перечисляют только имена variables |
| FastAPI auth | `get_current_user` остаётся источником claims; `get_current_user_id` — узкий adapter | Claims доступны там, где нужны, остальные endpoints получают только UID |
| Database DI | Один канонический `get_db`, service factories поверх него | Полные dependency overrides без реального Firebase/GCP |
| Packages | Top-level `app.*`, `ai.*`, `workers.*`, `telegrambot.*` | Совпадает с `/app` в Docker и локальным `cwd=backend` |
| AI | Внутренний analyzer port + Google ADK implementation с Pydantic output | SDK заменяем и тестируем без протекания его типов в worker |
| Firestore | `FieldFilter` и module-level transactional API | Соответствует установленному production SDK |
| Dependencies | Python 3.11-compatible lock/constraints, используемый Docker build | Исключает случайное обновление SDK между builds |

## 7. Фазы и порядок

| Порядок | Фаза | Основной deliverable | Gate |
|---:|---|---|---|
| 1 | 1.0 Baseline and contract freeze | Версии, defect matrix, test ownership и scope зафиксированы | Baseline воспроизводится |
| 2 | 1.1 Configuration lifecycle | Lazy settings, role validation, zero import side effects | Config tests passing, warnings removed |
| 3 | 1.2 FastAPI dependency injection | Routers и OpenAPI graph собираются с overrides | Все router imports и schema generation passing |
| 4 | 1.3 Package and runtime layout | Один import style и чистые worker imports | Imports проходят из `/app` layout |
| 5 | 1.4 Supported AI adapter | Поддерживаемый ADK runtime и validated structured output | AI tests не используют сеть |
| 6 | 1.5 Firestore SDK correctness | Реальные filters/transactions и честные test doubles | Query/transaction tests passing |
| 7 | 1.6 Runtime/container acceptance | API и workers доказаны в Python 3.11 image | Stage Definition of Done выполнен |

Фазы выполняются последовательно. Внутри фазы разрешены только небольшие атомарные commits, каждый из которых сохраняет passing состояние уже открытых gates.

## 8. Production implementation standards

- Полные type hints на public functions, providers и adapters.
- Никаких секретов, credential values, raw tokens или prompts с приватными данными в логах.
- Ошибки на boundaries переводятся в typed/domain errors с сохранением исходной причины через exception chaining.
- Network/SDK calls имеют явный timeout и retry policy только там, где операция идемпотентна.
- Routers не создают services вручную и не обращаются к Firestore напрямую.
- Workers не создают clients/settings при импорте и подтверждают сообщения только в своей business phase; ack/nack semantics этапа 2 не меняются здесь.
- Pydantic models валидируют диапазоны до side effects.
- Tests используют factories/fixtures и dependency overrides; unit suite не зависит от ADC, GCP project или интернета.
- Изменение SDK surface сопровождается regression test, который падает на прежней реализации.

## 9. Test strategy

### Unit and contract

- Settings construction, caching, cache reset и role-specific validation.
- Dependency providers и auth UID adapter через FastAPI overrides.
- AI adapter с fake runner/client: valid output, malformed output, timeout, retryable и terminal failure.
- Firestore filters и transactions с API-faithful fake/mocks.
- Skill boundaries: missing user, assessment range, weight range, clamping и безопасное имя concept.

### Import and application

- отдельный import каждого router;
- import `app.api.v1.router` и построение `app.openapi()`;
- import `app.main`, `workers.github_worker`, `workers.opportunity_worker` без credentials;
- TestClient `/health` возвращает 200 без вызова Telegram, Firestore или Gemini.

### Container

- clean Python 3.11 dependency install из lock/constraints;
- Docker image build из `backend/`;
- import smoke внутри image с пустым credential environment;
- API container health smoke с test-safe runtime configuration;
- worker module startup/import smoke без подключения к subscription;
- итоговый test suite без warnings этапа 1.

## 10. Phase gates и xfail policy

К этапу 1 относятся минимум следующие regression tests:

- config accessor;
- dependency exports;
- GitHub router import;
- FastAPI application import;
- supported ADK import;
- Docker-layout worker imports;
- Firestore filter API;
- Firestore transaction API.

Текущий transaction xfail не должен просто потерять marker: его следует заменить тестом фактического supported API и отдельным behavior test. Остальные xfail этапов 2–5 остаются неизменными.

## 11. Риски и mitigation

| Риск | Вероятность/влияние | Mitigation |
|---|---|---|
| Broad dependency ranges дают другой ADK API в clean build | Высокая/высокое | Зафиксировать Python 3.11 resolution до миграции AI |
| Config refactor снова ломает public health import | Средняя/высокое | Запрет import-time validation; отдельный import и lifespan test |
| Service factory migration меняет HTTP contract | Средняя/среднее | Snapshot generated OpenAPI до/после; public schema changes запрещены |
| ADK output отличается между model versions | Средняя/высокое | Pydantic validation, bounded retry, fake SDK tests, explicit model config |
| Firestore fake скрывает production incompatibility | Высокая/высокое | Удалить fake-only APIs; проверять imported SDK symbols и emulator-ready behavior |
| Docker gate недоступен локально | Сейчас/высокое | До фазы 1.6 запустить Docker daemon либо выполнить gate в CI; этап не закрывать без результата |

## 12. Rollback strategy

- Каждая фаза имеет отдельную commit boundary и не смешивается со следующей.
- При regression откатывается только текущая фаза; contracts предыдущих gates остаются стабильными.
- Compatibility aliases допускаются только как краткоживущие, side-effect-free adapters и удаляются до фазы 1.6.
- Старый unsupported AI path не сохраняется как fallback.
- Изменения Firestore data schema на этапе 1 запрещены, поэтому data migration/rollback не требуется.

## 13. Definition of Done этапа 1

Этап завершён только если одновременно:

1. clean Python 3.11 environment устанавливается из зафиксированного dependency set;
2. `app.main` и оба worker-модуля импортируются в Docker layout без credentials и network I/O;
3. FastAPI строит OpenAPI schema, а `/health` возвращает 200 в TestClient и container;
4. отсутствие обязательной production variable приводит к sanitised configuration error с именем variable;
5. GitHub analyzer использует поддерживаемый Google ADK API и валидирует structured output;
6. proficiency assessment и significance представлены разными validated fields;
7. Firestore filters/transactions используют production SDK API;
8. unit tests не требуют реальных GCP credentials;
9. все относящиеся к этапу strict xfail преобразованы в meaningful passing tests;
10. warnings, относящиеся к deprecated Pydantic env metadata, отсутствуют;
11. xfail этапов 2–5 не стали случайно passing из-за скрытого scope creep;
12. tracker обновлён только после прохождения соответствующих gates.

## 14. Approval gate

До явного утверждения плана:

- plan остаётся `planned`;
- все задачи остаются `pending`;
- implementation files не изменяются;
- фаза 1.0 не начинается.
