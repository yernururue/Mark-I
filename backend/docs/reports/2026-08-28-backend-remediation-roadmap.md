# Mark-I Backend — подробная дорожная карта исправления

> Дата: 2026-08-28  
> Область: только `backend/` и связанные backend-контракты  
> Основание: PRD, TRD, `openapi.yaml`, `docs/API.md`, `docs/FIRESTORE.md`, `docs/EVENTS.md`, код-ревью и PICT-сценарии  
> Формат: один документ, пять последовательных этапов

## 1. Назначение документа

Этот документ описывает не отдельные ошибки, а порядок восстановления backend как целой системы. Сейчас в проекте есть рабочие фрагменты бизнес-логики, однако приложение не собирается в единый запускаемый сервис, а несколько внутренних и внешних контрактов противоречат друг другу.

Исправления нужно выполнять последовательно:

```text
Этап 1. Запуск и базовые зависимости
    ↓
Этап 2. GitHub event pipeline
    ↓
Этап 3. API и Firestore-контракты
    ↓
Этап 4. Безопасность и deployment
    ↓
Этап 5. Полная бизнес-логика, производительность и E2E
```

Переходить к следующему этапу следует только после выполнения критериев готовности предыдущего. Например, нет смысла отлаживать GitHub webhook end-to-end, пока `app.main` не импортируется, а контракт API нельзя считать стабильным, пока producer и worker используют разные форматы событий.

## 2. Общие правила исправления

1. `openapi.yaml` должен стать каноническим источником REST API. Если продуктовое решение требует другой контракт, сначала изменяется OpenAPI, затем код, тесты и человекочитаемая документация.
2. `docs/FIRESTORE.md` должен быть каноническим источником формы документов Firestore.
3. Форматы Pub/Sub-сообщений должны быть описаны отдельными Pydantic-моделями и одинаково использоваться publisher и consumer.
4. Router отвечает только за HTTP: получить параметры, вызвать сервис, вернуть response. Firestore и внешние API должны находиться в service layer.
5. Известные дефекты сейчас отмечены `xfail(strict=True)`. После исправления каждой проблемы соответствующий тест переводится в обычный passing-тест.
6. Реальные токены, ключи и секреты не должны попадать в исходный код, тесты, Firestore или логи.

---

# Этап 1. Восстановить запуск приложения и базовую инфраструктуру

## Цель этапа

Добиться, чтобы FastAPI-приложение и оба worker-модуля импортировались и запускались в том же окружении, которое используется в Docker. На этом этапе бизнес-функции ещё могут быть неполными, но Python import graph, dependency injection, конфигурация, ADK и Firestore API должны быть технически корректными.

## Фаза 1.1. Унифицировать конфигурацию

### Проблема

`backend/app/config.py` создаёт глобальный объект:

```python
settings = Settings()
```

Но следующие модули импортируют отсутствующую функцию `get_settings()`:

- `ai/agent.py`;
- `ai/chat_agent.py`;
- `ai/analyzers/opportunity_analyzer.py`;
- `app/services/opportunity_service.py`;
- `workers/github_worker.py`;
- `workers/opportunity_worker.py`.

### Где расходятся контракты

| Участник | Ожидание |
|---|---|
| `app.dependencies` и часть API | Глобальный объект `settings` |
| AI, Opportunity и workers | Функция `get_settings()` |
| `cloudbuild.yaml` | Передаёт только `ENV=production` |
| `Settings` | Требует GCP, Telegram и GitHub variables уже во время импорта |

Из-за этого одна ошибка конфигурации блокирует импорт всего приложения, включая публичный `/health`.

Дополнительно Pydantic выдаёт предупреждения для всех конструкций `Field(..., env="...")`: этот способ deprecated и будет удалён в Pydantic v3.

### Связанные функции и классы

- `app.config.Settings`;
- глобальный `app.config.settings`;
- все места вызова `get_settings()`;
- `app.main.app`;
- `app.main.lifespan`.

### Пример проявления

```text
from app.config import get_settings
ImportError: cannot import name 'get_settings'
```

Даже после добавления функции container может завершиться с `ValidationError`, если Cloud Run не получил обязательный `GITHUB_CLIENT_SECRET` или другой параметр.

### Примерное решение

Выбрать единый способ получения конфигурации. Для FastAPI удобнее cached factory:

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

После этого:

- сервисы получают `Settings` через `get_settings()` или FastAPI `Depends`;
- модульный `settings` либо удаляется, либо временно становится `settings = get_settings()` для совместимости;
- Pydantic config переводится на актуальный `SettingsConfigDict` без deprecated `env` arguments;
- production startup явно проверяет обязательные параметры и сообщает имена отсутствующих variables без вывода их значений.

### Критерии готовности

- `from app.config import get_settings` выполняется без ошибки;
- два вызова `get_settings()` возвращают один cached instance;
- тестовая конфигурация создаётся без чтения реальных секретов;
- Pydantic deprecation warnings устранены;
- отсутствие production secret приводит к понятной configuration error, а не к неочевидному import chain failure.

## Фаза 1.2. Восстановить FastAPI dependency injection

### Проблема

`chat.py`, `dashboard.py`, `skills.py`, `observations.py`, `telegram.py`, `triggers.py` и Telegram webhook импортируют:

```python
get_db
get_current_user_id
```

Но `app/dependencies.py` предоставляет только `get_firestore_client()` и GitHub service factory. Проверка пользователя существует отдельно как `app.middleware.auth.get_current_user()`.

В `app/api/v1/github.py` две функции используют неопределённую dependency `_get_github_service`, хотя правильная `get_github_service` уже импортирована.

### Где расходятся контракты

| Router | Фактическая dependency | Существующая реализация |
|---|---|---|
| Users | `get_firestore_client`, `get_current_user` | Работает по текущей схеме |
| Chat/Dashboard/Skills/Observations/Telegram | `get_db`, `get_current_user_id` | Функций нет |
| GitHub auth/callback/list | `get_github_service` | Функция есть |
| GitHub select/disconnect | `_get_github_service` | Функции нет |

### Связанные функции

- `app.dependencies.get_firestore_client()`;
- `app.middleware.auth.get_current_user()`;
- `app.dependencies.get_github_service()`;
- все route functions в `app/api/v1/`;
- `app.api.v1.router.api_v1_router`.

### Пример проявления

FastAPI импортирует router, Python пытается вычислить `Depends(_get_github_service)` и получает `NameError`. Это происходит до первого HTTP-запроса.

### Примерное решение

Не переписывать все routers одновременно, а создать явные универсальные dependencies:

```python
def get_db() -> FirestoreClient:
    return get_firestore_client()

def get_current_user_id(
    current_user: dict = Depends(get_current_user),
) -> str:
    return current_user["uid"]
```

Затем:

- заменить `_get_github_service` на `get_github_service`;
- выбрать один стиль во всех routers: либо dependency возвращает весь `current_user`, либо только `uid`;
- постепенно добавить service factories для Chat, Telegram, Observation, Skill и Dashboard;
- не создавать service objects вручную внутри endpoint.

### Критерии готовности

- каждый модуль `app.api.v1.*` импортируется отдельно;
- `app.api.v1.router` импортируется полностью;
- FastAPI может построить OpenAPI schema;
- dependency overrides позволяют тестам подменить Firestore и authentication.

## Фаза 1.3. Унифицировать Python package layout

### Проблема

Dockerfile копирует содержимое `backend/` непосредственно в `/app`:

```text
/app/app
/app/ai
/app/workers
/app/telegrambot
```

При такой структуре корректны импорты `app.*`, `ai.*`, `workers.*`. Однако workers и AI analyzer используют `backend.app.*` и `backend.ai.*`.

### Связанные модули

- `workers/github_worker.py`;
- `workers/opportunity_worker.py`;
- `ai/agent.py`;
- `ai/analyzers/github_analyzer.py`;
- `Dockerfile`;
- команды `python -m workers.*` в `cloudbuild.yaml`.

### Пример проявления

```text
ModuleNotFoundError: No module named 'backend'
```

Локальный запуск из корня репозитория может случайно скрыть проблему, потому что родительская директория присутствует в `sys.path`. Docker использует другой working directory.

### Примерное решение

Для текущего Dockerfile проще выбрать top-level layout:

```python
from app.config import get_settings
from ai.analyzers.github_analyzer import analyze_github_event
from app.services.observation_service import ObservationService
```

Альтернативный вариант — сделать `backend` настоящим package, копировать весь репозиторий и изменить `WORKDIR`/`PYTHONPATH`. Этот вариант затронет больше deployment-кода и сейчас не рекомендуется.

### Критерии готовности

- одинаковые imports используются локально и в Docker;
- `python -m workers.github_worker` запускает модуль из `/app`;
- `python -m workers.opportunity_worker` запускает модуль из `/app`;
- imports не зависят от запуска из корня монорепозитория.

## Фаза 1.4. Заменить неподдерживаемый AI/ADK API

### Проблема

`ai/agent.py` и `ai/analyzers/github_analyzer.py` используют:

```python
from google.antigravity import LocalAgentConfig, Agent
```

Установленный `google-adk` не предоставляет модуль `google.antigravity`. При этом Chat и Opportunity используют другой стек — `vertexai.generative_models`.

### Где расходится архитектура

| Компонент | Текущая технология |
|---|---|
| GitHub Analyzer | Несуществующий `google.antigravity` API |
| Chat Agent | Vertex AI `GenerativeModel` |
| Opportunity Analyzer | Vertex AI `GenerativeModel` |
| TRD | Заявлен единый Google ADK Agent |

Фактически сейчас нет единого AI adapter и нет гарантии одинаковой обработки retries, structured output, safety settings и model configuration.

### Связанные функции и модели

- `ai.agent.get_github_analyzer_config()`;
- `ai.agent.GithubObservationSchema`;
- `ai.analyzers.github_analyzer.analyze_github_event()`;
- `ai.chat_agent.ChatAgent`;
- `ai.analyzers.opportunity_analyzer.OpportunityAnalyzer`;
- `Settings.GEMINI_MODEL`.

### Примерное решение

Сначала проверить API именно установленной версии `google-adk`, затем создать внутренний adapter, чтобы business code не зависел от конкретного SDK:

```python
class GitHubAnalyzer:
    async def analyze(self, event: GitHubEventContext) -> GitHubAnalysis:
        ...
```

Внутри adapter может использовать актуальный ADK Agent или `google-genai`, но worker должен знать только входную и выходную Pydantic-модель.

Выходную модель следует расширить:

```python
class GitHubAnalysis(BaseModel):
    summary: str
    concept: str
    sentiment: Literal["positive", "negative", "neutral"]
    proficiencyAssessment: float  # 0..10, влияет на skill
    significanceScore: int         # 1..10, влияет на notification
```

Это отделит оценку навыка от важности события. Сейчас worker ошибочно использует `significanceScore` как proficiency assessment.

### Критерии готовности

- GitHub analyzer импортируется без `google.antigravity`;
- Gemini/ADK client подменяется в unit tests;
- structured output валидируется Pydantic-моделью;
- AI failure не приводит к созданию частично заполненной observation;
- skill assessment и notification significance являются разными полями.

## Фаза 1.5. Исправить использование Firestore SDK

### Проблема A: transaction decorator

`SkillService.update_skill()` использует `self._db.transactional`, которого нет у Firestore Client.

### Проблема B: query filters

`UserService` и `ObservationService` передают tuple в `where(filter=...)`. Установленный SDK ожидает `FieldFilter`.

### Связанные функции

- `SkillService.update_skill()`;
- `UserService.get_user_by_telegram_id()`;
- `ObservationService.get_recent_observations()`;
- `ObservationService.get_observation_count()`.

### Примерное решение

```python
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

query = collection.where(
    filter=FieldFilter("concept", "==", concept)
)

@firestore.transactional
def update_in_transaction(transaction, doc_ref):
    ...
```

Кроме синтаксиса нужно определить поведение при отсутствии user document и проверить диапазон assessment. Значение должно быть ограничено `0..10` до записи.

### Критерии готовности этапа 1

- `from app.main import app` выполняется успешно;
- `/health` отвечает `200` в TestClient и Docker container;
- оба worker-модуля импортируются в Docker layout;
- Firestore query tests используют реальный API shape;
- xfail-тесты startup/config/dependencies/imports/Firestore переведены в passing;
- ни один unit test не требует реальных GCP credentials.

---

# Этап 2. Восстановить GitHub webhook → Pub/Sub → worker pipeline

## Цель этапа

Гарантировать, что каждый поддерживаемый GitHub event получает правильного пользователя, обрабатывается не более одного раза с точки зрения бизнес-эффектов и создаёт полный набор данных: observation, skill update, decision и при необходимости notification.

## Фаза 2.1. Определить единый event envelope

### Проблема

Publisher создаёт:

```json
{
  "deliveryId": "delivery-1",
  "eventType": "push",
  "repoFullName": "alex/project",
  "payload": {},
  "receivedAt": "..."
}
```

Worker читает:

```python
uid = data.get("uid")
event_type = data.get("event_type")
```

`uid` publisher вообще не передаёт, а `eventType` и `event_type` отличаются регистром и стилем имени.

### Связанные функции

- `receive_github_webhook()`;
- `GitHubService.publish_event()`;
- `github_worker.process_message_async()`;
- `GitHubService.select_repos()`;
- поле `users/{uid}.connectedRepos`.

### Пример проявления

Webhook возвращает GitHub `200 OK`, Pub/Sub доставляет сообщение, worker не находит `uid`, выполняет `ack()` и молча пропускает событие.

### Примерное решение

Создать общую модель, импортируемую publisher и worker:

```python
class GitHubEventEnvelope(BaseModel):
    schemaVersion: Literal[1] = 1
    deliveryId: str
    eventType: str
    uid: str
    repoFullName: str
    payload: dict
    receivedAt: datetime
```

До публикации webhook должен определить пользователя по `connectedRepos`. Если один repo разрешено подключить нескольким Mark-I users, publisher создаёт отдельное сообщение для каждого `uid`.

Если пользователь не найден, receiver возвращает `200`, но пишет структурированный warning с `deliveryId` и `repoFullName`.

### Критерии готовности

- publisher и consumer используют одну Pydantic-модель;
- snake_case/camelCase не преобразуются вручную в разных местах;
- любое опубликованное сообщение содержит `uid`;
- schema version позволяет безопасно менять формат позже.

## Фаза 2.2. Реализовать идемпотентность и безопасные retries

### Проблема

`docs/EVENTS.md` требует `processed_events`, но receiver и worker эту коллекцию не используют. Pub/Sub работает по модели at-least-once и может доставить одно событие повторно.

### Возможные последствия

Один push может:

- создать две observations;
- дважды изменить skill score;
- создать две decisions;
- отправить два Telegram-сообщения.

### Связанные функции и данные

- `receive_github_webhook()`;
- `process_message_async()`;
- `ObservationService.create_observation()`;
- `SkillService.update_skill()`;
- `DecisionService.evaluate_and_log()`;
- `processed_events/{eventId}`.

### Примерное решение

Использовать документ с детерминированным ID:

```text
processed_events/github:{deliveryId}:{uid}
```

Минимальное состояние:

```json
{
  "source": "github",
  "deliveryId": "delivery-1",
  "userId": "user-1",
  "status": "processing",
  "startedAt": "...",
  "completedAt": null
}
```

Worker в Firestore transaction проверяет документ:

1. `completed` → `ack` без повторных side effects;
2. отсутствует → создать `processing` и начать работу;
3. `processing` слишком долго → разрешить retry по timeout policy;
4. после всех записей и notification → `completed`.

Для более строгой exactly-once семантики observation ID также должен быть детерминированным, например `github-{deliveryId}-{uid}`. Тогда повторный worker не создаст второй документ даже после сбоя между Firestore write и `completed` marker.

### Критерии готовности

- повторная доставка одного Pub/Sub message не меняет skill второй раз;
- повторная доставка не отправляет второе уведомление;
- `ack` выполняется только для завершённого или уже обработанного события;
- recoverable error приводит к `nack`, а не к silent skip.

## Фаза 2.3. Разделить обработку GitHub event types

### Проблема

`get_changes_text()` извлекает данные только из `push` и `pull_request`. Для `pull_request_review`, `issues`, `issue_comment` и `create` prompt почти пустой.

### Связанные функции

- `github_worker.get_changes_text()`;
- `analyze_github_event()`;
- `GITHUB_ANALYZER_USER_PROMPT_TEMPLATE`;
- список events в `GitHubService.select_repos()`.

### Примерное решение

Создать отдельные extractors с общей выходной моделью:

```python
EVENT_EXTRACTORS = {
    "push": extract_push,
    "pull_request": extract_pull_request,
    "pull_request_review": extract_review,
    "issues": extract_issue,
    "issue_comment": extract_issue_comment,
    "create": extract_create,
}
```

Каждый extractor возвращает:

```python
class GitHubEventContext(BaseModel):
    repo: str
    eventType: str
    ref: str | None
    title: str | None
    description: str | None
    changesText: str
    metadata: dict
```

Примеры:

- `pull_request_review` → body review, state, pull request URL;
- `issues` → action, title, body, labels;
- `issue_comment` → comment body и issue/PR context;
- `create` → ref type и ref name.

Unknown event должен быть явно залогирован и подтверждён без AI-вызова.

### Критерии готовности

- все документированные event types имеют отдельные tests;
- ни один поддерживаемый event не отправляет пустой prompt;
- unsupported event не создаёт observation;
- metadata сохраняет `deliveryId`, repo, event и source reference.

## Фаза 2.4. Исправить skill assessment и escalation flags

### Проблема A

Worker использует `significanceScore` как assessment для навыка. Но significance отвечает на вопрос «насколько событие важно», а proficiency — «насколько хорошо пользователь владеет концептом».

Например, большой архитектурный commit может иметь significance `9`, но качество реализации может соответствовать proficiency `5`. Текущий код установит навык почти на `9`.

### Проблема B

`DecisionService` знает flags:

- `repeated_error`;
- `skill_regression`;
- `new_concept`;
- `milestone_reached`.

Worker передаёт `negative_sentiment`, которого нет в `ESCALATION_RULES`. Следовательно, escalation никогда не срабатывает через текущий worker.

### Связанные функции

- `GithubObservationSchema`;
- `SkillService.update_skill()`;
- `DecisionService.evaluate_and_log()`;
- `github_worker.process_message_async()`.

### Примерное решение

1. Gemini возвращает отдельный `proficiencyAssessment`.
2. До skill update сохранить старый score.
3. После update вычислить flags детерминированным Python-кодом:
   - skill отсутствовал → `new_concept`;
   - score уменьшился минимум на 1 → `skill_regression`;
   - score пересёк 5 или 8 → `milestone_reached`;
   - последние три negative observations по concept → `repeated_error`.
4. Передать только поддерживаемые flags в DecisionService.

### Критерии готовности этапа 2

- реальный event envelope проходит receiver → publisher → worker без преобразования ключей вручную;
- duplicate delivery не создаёт повторных эффектов;
- все шесть GitHub event types покрыты extractor tests;
- skill обновляется по proficiency, decision — по significance;
- escalation cases из PICT проходят без `xfail`;
- delivery ID присутствует в observation metadata и processed event.

---

# Этап 3. Синхронизировать REST API, Firestore и продуктовые контракты

## Цель этапа

Сделать так, чтобы frontend, OpenAPI, Pydantic models, routers, services и Firestore использовали одинаковые названия полей, URL, правила валидации и pagination semantics.

## Фаза 3.1. Зафиксировать канонический контракт и compatibility policy

### Проблема

Сейчас одновременно существуют четыре версии истины:

- `openapi.yaml`;
- `docs/API.md`;
- Pydantic models;
- PICT expectations.

Изменения делались в коде без синхронного обновления остальных источников.

### Примерное решение

1. Считать `openapi.yaml` каноническим.
2. На каждую schema добавить contract test против FastAPI-generated OpenAPI.
3. После согласования автоматически или вручную обновить `docs/API.md`.
4. Breaking changes делать либо до первого production release, либо через `/api/v2`.

### Критерий

FastAPI-generated schema и `openapi.yaml` не имеют неожиданных различий по paths, methods, required fields и response shapes.

## Фаза 3.2. Исправить Chat API и unified history

### Текущее расхождение

| Область | OpenAPI | Код |
|---|---|---|
| Request text | `message` | `text` |
| Channel | обязательный `web/telegram` | отсутствует в request, всегда `web` |
| Length | `1..2000` | ограничений нет |
| Response text | `response` | `text` |
| IDs | `messageId`, `agentMessageId` | отсутствуют |
| History response | object с pagination | простой список |

### Связанные функции и модели

- `models.chat.ChatRequest`;
- `models.chat.ChatResponse`;
- `api.v1.chat.process_chat_message()`;
- `api.v1.chat.get_chat_messages()`;
- `ChatService.process_message()`;
- `ChatAgent.generate_response()`.

### Пример проявления

Frontend отправляет:

```json
{"message": "What should I learn?", "channel": "web"}
```

Backend ожидает `text` и отвечает `422`.

### Примерное решение

```python
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    channel: Literal["web", "telegram"]

class ChatResponse(BaseModel):
    response: str
    messageId: str
    agentMessageId: str
```

`ChatService.process_message()` должен возвращать result object с обоими IDs, а не только строку. Получение истории нужно переместить из router в ChatService и добавить `limit`, `cursor`, `channel`.

### Критерии готовности

- empty и oversized messages получают `422`;
- web и Telegram используют один service и одну Firestore collection;
- response IDs соответствуют реально сохранённым документам;
- history имеет стабильную сортировку и cursor pagination.

## Фаза 3.3. Исправить Observations API

### Текущее расхождение

OpenAPI ожидает:

```json
{
  "observations": [],
  "nextCursor": null,
  "hasMore": false
}
```

Код возвращает `items` и `nextCursor`, но не `hasMore`. Параметры `source` и `cursor` принимаются endpoint, однако `source` не передаётся в service, а cursor полностью игнорируется.

### Связанные функции

- `api.v1.observations.get_observations()`;
- `ObservationService.get_recent_observations()`;
- `models.observation.ObservationsResponse`;
- Firestore composite indexes для `source + createdAt` и `concept + createdAt`.

### Примерное решение

Расширить service:

```python
def get_observations(
    uid: str,
    limit: int,
    cursor: ObservationCursor | None,
    source: str | None,
    concept: str | None,
) -> ObservationPage:
    ...
```

Cursor должен кодировать как минимум `createdAt` и document ID для стабильной сортировки. Query запрашивает `limit + 1`; дополнительный документ определяет `hasMore`.

### Критерии готовности

- `source=github` исключает chat/opportunity observations;
- `concept=recursion` фильтрует concept;
- переход по `nextCursor` не возвращает дубликаты;
- response shape полностью совпадает с OpenAPI.

## Фаза 3.4. Исправить Telegram API и Firestore schema

### Текущее расхождение

| Область | Документация | Код |
|---|---|---|
| Link response | `linkCode`, `expiresAt`, `botUsername` | только `code` |
| Unlink route | `DELETE /telegram/unlink` | `DELETE /telegram/link` |
| Chat destination | `telegramChatId` | не сохраняется |
| Unlink logic | service layer | прямой Firestore update в router |
| Already linked | ожидается `409` | явно не проверяется |

### Связанные функции

- `TelegramService.generate_link_code()`;
- `TelegramService.validate_and_link()`;
- `api.v1.telegram.generate_telegram_link()`;
- `api.v1.telegram.unlink_telegram()`;
- `telegrambot.handlers._handle_link()`;
- `UserService._firestore_to_profile()`.

### Примерное решение

`generate_link_code()` возвращает не строку, а объект:

```python
class TelegramLink:
    code: str
    expires_at: datetime
```

Router преобразует его в documented response. `validate_and_link()` должен получать отдельно `telegram_user_id` и `telegram_chat_id`, сохранять оба значения и использовать transaction, чтобы один code нельзя было одновременно активировать дважды.

Unlink переносится в `TelegramService.unlink(uid)` и очищает:

- `telegramUserId`;
- `telegramChatId`;
- `telegramUsername`;
- временные link codes пользователя.

Поле `telegramLinked` лучше не хранить отдельно, а вычислять из `telegramUserId/telegramChatId`, иначе возникает schema drift.

### Критерии готовности

- response содержит три documented fields;
- route использует `/telegram/unlink`;
- private и group chat IDs не смешиваются;
- повторное использование code невозможно;
- unlink является идемпотентным и находится в service layer.

## Фаза 3.5. Синхронизировать Dashboard и Decisions

### Dashboard divergence

OpenAPI ожидает `totalSkills`, `streakDays`, `lastActivityAt`. Код возвращает `totalDecisions`, `activeSkills`, `overallTrend`. Decisions сейчас вообще заменены пустым списком.

### Decision divergence

Firestore docs ожидают:

```text
action, threshold, intensity
```

Код хранит:

```text
shouldNotify, intensityThreshold
```

### Связанные функции и модели

- `api.v1.dashboard.get_dashboard()`;
- `models.dashboard.DashboardStats`;
- `models.dashboard.DashboardResponse`;
- `DecisionService.evaluate_and_log()`;
- `models.decision.Decision`;
- `users/{uid}/decisions`.

### Примерное решение

Выбрать documented decision schema и дополнить её delivery status:

```json
{
  "action": "notified",
  "shouldNotify": true,
  "threshold": 5,
  "intensity": "normal",
  "deliveryStatus": "sent"
}
```

`shouldNotify` может остаться внутренним boolean, но frontend-friendly `action` должен однозначно показывать решение. DashboardService должен агрегировать реальные skills, observations и decisions, а не создавать mock values в router.

### Критерии готовности

- Dashboard не содержит mock decisions/trend;
- Decision documents соответствуют Firestore docs;
- response model и OpenAPI совпадают;
- decisionLimit реально применяется.

## Фаза 3.6. Разрешить противоречие профиля и goal

### Проблема

PICT использует свободные цели:

```text
Get a job at Google
Master full-stack development
```

`docs/API.md` разрешает только `job`, `leetcode`, `stack:<name>`. Текущий Pydantic model принимает любую строку.

PICT также ожидает `skills={}` в profile response, но `UserProfile` и OpenAPI не возвращают skills — для них существует отдельный `/skills` endpoint.

### Связанные модели

- `CreateProfileRequest`;
- `UpdateProfileRequest`;
- `UserProfile`;
- `UserService.create_profile()`;
- onboarding frontend contract.

### Рекомендуемое MVP-решение

Оставить `goal` свободным текстом с ограничением, например `1..500`, потому что это соответствует PRD и персонализированному AI mentor. Обновить `openapi.yaml` и `docs/API.md`.

Более структурированный вариант для будущей версии:

```json
{
  "goalType": "job",
  "goalDescription": "Get a backend job at Google"
}
```

`skills` рекомендуется не добавлять в profile response, чтобы не дублировать `/skills`; вместо этого нужно исправить ожидание PICT.

## Фаза 3.7. Унифицировать ошибки

### Проблема

Документация обещает:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "..."}}
```

Однако стандартные FastAPI/Pydantic validation errors используют `detail`. Некоторые endpoints передают nested error в `HTTPException.detail`, что даёт дополнительный уровень `detail.error`.

### Примерное решение

Добавить exception handlers для:

- `RequestValidationError`;
- `HTTPException`;
- domain exceptions;
- unexpected errors.

Создать domain errors (`NotFoundError`, `ConflictError`, `ExternalServiceError`) и преобразовывать их в HTTP только на API-границе.

### Критерии готовности этапа 3

- FastAPI OpenAPI совпадает с `openapi.yaml`;
- Chat, Observations, Telegram, Dashboard, Decision и Profile contract tests проходят;
- PICT исправлен там, где он противоречит каноническому API;
- routers не обращаются к Firestore напрямую;
- ошибки имеют одинаковый JSON shape.

---

# Этап 4. Закрыть безопасность и сделать deployment воспроизводимым

## Цель этапа

Исключить публичный запуск дорогих pipeline, fail-open webhook validation и неявные production settings. Один и тот же commit должен воспроизводимо собираться, запускаться и проходить smoke tests в container/staging.

## Фаза 4.1. Защитить Opportunity trigger

### Проблема

`POST /api/v1/trigger/opportunities` не имеет authentication dependency. Cloud Run API разворачивается с `--allow-unauthenticated`, поэтому любой клиент может запустить Dev.to fetch, Pub/Sub и последующие Gemini calls.

### Связанные компоненты

- `api.v1.triggers.trigger_opportunities()`;
- Cloud Scheduler;
- `OpportunityService.fetch_and_publish_opportunities()`;
- `cloudbuild.yaml`;
- Cloud Run IAM.

### Рекомендуемое решение

Предпочтительно использовать Cloud Scheduler с OIDC и закрытый internal endpoint или Cloud Run Job. Если API service остаётся publicly reachable, endpoint должен валидировать Google-signed identity token с ожидаемой service account audience.

Shared secret header допустим как временное MVP-решение, но слабее OIDC и требует rotation.

### Критерии готовности

- анонимный запрос получает `401/403`;
- Scheduler service account успешно запускает pipeline;
- повторные или слишком частые triggers имеют idempotency/rate control;
- trigger не находится среди обычных user-facing routes без отдельной защиты.

## Фаза 4.2. Сделать Telegram webhook fail-closed

### Проблема

Проверка применяется только если `TELEGRAM_WEBHOOK_SECRET` настроен. Ошибка конфигурации выключает безопасность.

### Связанные функции

- `api.webhooks.telegram.telegram_webhook()`;
- `telegrambot.bot.setup_webhook()`;
- environment `TELEGRAM_WEBHOOK_SECRET`.

### Примерное решение

- в production `TELEGRAM_WEBHOOK_SECRET` является обязательным Settings field;
- webhook отклоняет запрос, если server secret отсутствует;
- сравнение выполняется через `secrets.compare_digest`;
- JSON parse errors возвращают контролируемый response;
- `update_id` используется для optional deduplication.

### Критерии готовности

- missing/wrong header всегда отклоняется в production;
- correct header принимается;
- secret не появляется в логах;
- Telegram webhook registration и validation используют одно значение.

## Фаза 4.3. Ограничить размеры запросов и частоту вызовов

### Проблема

Chat не ограничивает длину, GitHub webhook читает всё тело через `await request.body()`, а rate limiting отсутствует.

### Связанные endpoints

- `POST /chat`;
- GitHub webhook;
- Telegram webhook;
- Opportunity trigger.

### Примерное решение

- Chat: Pydantic `min_length=1`, `max_length=2000`;
- webhook: проверить `Content-Length` и установить разумный предел payload;
- API Gateway/Cloud Armor или application limiter для user endpoints;
- ограничить число function calls и Gemini prompt size;
- логировать rejection без сохранения тела запроса.

### Критерии готовности

- oversized requests отклоняются до Gemini/Firestore;
- нагрузочный тест не создаёт неограниченное число внешних вызовов;
- limits документированы в OpenAPI.

## Фаза 4.4. Настроить secrets и Cloud Run environment

### Проблема

`Settings` требует множество параметров, а `cloudbuild.yaml` передаёт только `ENV=production`. Первый deployment может собрать image, но container завершится при startup.

### Необходимые значения

- `GCP_PROJECT_ID`;
- `FIRESTORE_DATABASE`;
- `GEMINI_MODEL`;
- `TELEGRAM_BOT_USERNAME`;
- GitHub client ID;
- Pub/Sub topic names;
- frontend/backend URLs.

### Секреты

- GitHub client secret;
- GitHub webhook secret;
- Telegram bot token;
- Telegram webhook secret.

### Примерное решение

Обычные настройки передавать через `--set-env-vars`, секреты — через Cloud Run `--set-secrets` с Secret Manager references. Cloud Build service account получает только необходимые IAM roles.

Не следует помещать значения секретов непосредственно в YAML или command output.

### Критерии готовности

- новый Cloud Run service можно развернуть с нуля;
- container startup не зависит от старых вручную настроенных variables;
- secrets читаются из Secret Manager;
- deployment documentation содержит список имён, но не значений.

## Фаза 4.5. Унифицировать HTTP clients и lifecycle

### Проблема

Проект создаёт несколько `httpx.AsyncClient` разными способами:

- singleton в `app.dependencies`;
- отдельный module-level client в TelegramService;
- новый client на каждый Opportunity fetch;
- новый client при Telegram webhook setup.

Это создаёт разные timeout/retry policies и усложняет корректное закрытие connections.

### Примерное решение

Передавать один application-level client через DI. Для workers создавать client в lifespan/main context и передавать services. Определить разные timeout profiles для GitHub, Telegram и Dev.to, но использовать один механизм создания.

### Критерии готовности

- все долгоживущие clients закрываются;
- tests могут подменить HTTP transport;
- timeout/retry policy явна для каждого внешнего сервиса;
- нет нового client на каждый article или message.

## Фаза 4.6. Добавить container и staging smoke tests

### Проблема

Локальная среда использует Python 3.14, Docker — Python 3.11. Само различие не является ошибкой, но текущая проверка не доказывает совместимость production runtime.

### Примерное решение

В CI:

1. собрать Docker image;
2. запустить с test settings;
3. проверить `/health`;
4. проверить FastAPI OpenAPI generation;
5. импортировать/запустить worker entrypoints без подключения к real subscription;
6. выполнить pytest на Python 3.11.

### Критерии готовности этапа 4

- public trigger защищён;
- Telegram webhook fail-closed;
- secrets и env полностью задаются deployment pipeline;
- container smoke test проходит на Python 3.11;
- request size limits и rate controls проверяются tests;
- Cloud Run revision становится healthy без ручной донастройки.

---

# Этап 5. Завершить бизнес-логику, производительность и настоящий E2E

## Цель этапа

После восстановления запуска, pipeline, контрактов и безопасности довести систему до поведения, обещанного PRD: данные создаются независимо от наличия Telegram, decision policy действительно использует escalation rules, Dashboard показывает реальные данные, а основные пользовательские пути проверяются в staging end-to-end.

## Фаза 5.1. Исправить Opportunity semantics и deduplication

### Проблема A: unlinked users пропускаются

`process_opportunity_for_user()` делает return, если отсутствует `telegram_user_id`. Это противоречит F12 и PICT: observation и decision должны сохраняться, Telegram влияет только на доставку сообщения.

### Проблема B: разный relevance threshold

- PICT и текущий код: `>= 7`;
- `docs/EVENTS.md`: `>= 6`.

### Проблема C: global dedup выполняется слишком рано

`OpportunityService` записывает article в `processed_events` сразу после публикации. Это подтверждает, что article был отправлен в Pub/Sub, но не что он обработан для каждого пользователя. Новый пользователь также никогда не увидит ранее собранный article.

### Связанные функции

- `OpportunityService.fetch_and_publish_opportunities()`;
- `opportunity_worker.process_message_async()`;
- `process_opportunity_for_user()`;
- `OpportunityAnalyzer.analyze_opportunity()`;
- `ObservationService.create_observation()`;
- `DecisionService.evaluate_and_log()`.

### Рекомендуемое решение

1. Зафиксировать threshold `7` для MVP и обновить `EVENTS.md`.
2. Разделить global collection и per-user processing:
   - `collected_opportunities/{eventId}` — article уже получен из источника;
   - `users/{uid}/processed_opportunities/{eventId}` — article оценён для пользователя.
3. Проверять только наличие goal перед Gemini analysis.
4. При relevance `>= 7` всегда создавать observation и decision.
5. Telegram send выполнять только если `shouldNotify` и есть `telegramChatId`.

### Критерии готовности

- пользователь без Telegram видит opportunity на Dashboard;
- decision сохраняется даже без доставки;
- один пользователь не получает один article повторно;
- новый пользователь может получить актуальный ранее собранный article;
- threshold одинаков в коде, PICT и документации.

## Фаза 5.2. Полностью реализовать Decision Policy

### Проблема

Threshold logic работает, но реальный pipeline не генерирует documented escalation flags. Кроме того, decision schema не разделяет решение и результат доставки.

### Связанные функции

- `DecisionService.evaluate_and_log()`;
- GitHub worker;
- Opportunity worker;
- SkillService;
- TelegramService.

### Примерное решение

Разделить три понятия:

```text
shouldNotify   — решение policy
action         — notified / silent
deliveryStatus — sent / not-linked / failed / not-required
```

Например, при significance `8`, brutal intensity и отсутствии Telegram:

```json
{
  "shouldNotify": true,
  "action": "notified",
  "deliveryStatus": "not-linked",
  "reason": "Significance 8 >= threshold 3"
}
```

Если продукт считает `action=notified` только фактическую доставку, тогда лучше использовать `decision=notify/silent` и `deliveryStatus` отдельно. Главное — один раз зафиксировать семантику.

### Критерии готовности

- все 12 PICT decision cases проходят;
- каждый flag генерируется реальным pipeline test;
- decision всегда объясним;
- Telegram failure не удаляет decision и observation.

## Фаза 5.3. Устранить N+1 и mock Dashboard data

### Проблема

`SkillService.get_skills()` выполняет отдельный count query для каждого skill. Для 20 skills это минимум 21 Firestore call. Dashboard вызывает этот service и дополнительные queries, а decisions и trend пока mock.

### Связанные функции

- `SkillService.get_skills()`;
- `ObservationService.get_observation_count()`;
- `api.v1.dashboard.get_dashboard()`;
- user document `skills`.

### Примерное решение

Денормализовать skill metadata:

```json
"skills": {
  "testing": {
    "score": 6.2,
    "observationCount": 3,
    "lastUpdated": "...",
    "trend": "up"
  }
}
```

Если сохранение простой map `skill -> score` важно для frontend, можно создать отдельную subcollection `users/{uid}/skills/{skill}` или хранить два согласованных поля через одну transaction.

Dashboard aggregation должна находиться в `DashboardService`, а не в router.

### Критерии готовности

- число Firestore requests не растёт линейно по числу skills;
- Dashboard возвращает реальные decisions;
- trend и lastUpdated имеют определённую бизнес-логику;
- NFR dashboard `< 3 seconds` измеряется тестом.

## Фаза 5.4. Укрепить Chat Agent

### Проблемы

- function-calling loop не имеет максимального числа итераций;
- AI error превращается в generic строку, но нет structured error telemetry;
- API history pagination отсутствует;
- текущий tool set ограничен skills и observations, хотя TRD перечисляет больше tools;
- channel из web request сейчас не контролируется контрактом.

### Связанные функции

- `ChatAgent.generate_response()`;
- `_get_user_skills()`;
- `_get_recent_observations()`;
- `ChatService.process_message()`;
- `get_chat_messages()`.

### Примерное решение

- ограничить tool loop, например пятью вызовами;
- разрешать только зарегистрированные tools;
- логировать correlation ID, latency и тип AI failure без user content;
- хранить fallback response как agent message, но отдельно отмечать processing status;
- реализовать documented pagination;
- добавить tools постепенно и покрыть каждый permission test.

### Критерии готовности

- бесконечный tool loop невозможен;
- Gemini timeout возвращает безопасный response;
- последовательные web/Telegram messages используют общую историю;
- PICT chat cases выполняются с fake model и staging model.

## Фаза 5.5. Добавить integration и staging E2E tests

### Почему текущих tests недостаточно

Добавленные 96 tests проверяют детерминированную логику и фиксируют известные contracts, но PICT называет сценарии end-to-end. Настоящий E2E должен доказать работу внешних границ.

### Необходимая test pyramid

1. Unit tests — services, models, policy, extractors.
2. Contract tests — FastAPI vs OpenAPI, Pub/Sub envelope, Firestore document shape.
3. Emulator integration — Firebase Auth/Firestore/Pub/Sub emulator или контролируемый test project.
4. Staging E2E — GitHub test repository, Telegram test bot, deployed Cloud Run, Gemini test model/quota.

### Пример E2E GitHub case

```text
Создать test user
→ подключить test repo
→ отправить signed webhook delivery-123
→ дождаться processed_events delivery-123=completed
→ проверить одну observation
→ проверить одно skill update
→ проверить одну decision
→ повторить webhook
→ убедиться, что количество документов не изменилось
```

### Пример E2E Opportunity case без Telegram

```text
Создать user с goal, но без telegramChatId
→ передать opportunity relevance=8
→ проверить observation
→ проверить decision shouldNotify=true
→ проверить deliveryStatus=not-linked
→ убедиться, что Telegram API не вызывался
```

### Критерии готовности

- все 83 исходных PICT cases имеют traceability: unit, integration или staging E2E;
- нет неопределённых формулировок «should handle gracefully» — у каждого case есть точный status/data expectation;
- внешние tests используют отдельные test credentials;
- test cleanup удаляет созданные webhooks, documents и secrets.

## Фаза 5.6. Закрыть документацию и tracker

### Проблема

Backend tracker говорит `shipped`, хотя startup и core pipeline сейчас сломаны. Документация содержит разные thresholds, routes и response shapes.

### Примерное решение

После выполнения этапов:

- обновить `openapi.yaml`;
- синхронизировать `docs/API.md`, `docs/FIRESTORE.md`, `docs/EVENTS.md`, TRD;
- обновить PICT expectations;
- снять все исправленные strict xfail;
- только после container и staging smoke tests обновить backend/global tracker.

### Критерии готовности этапа 5

- core PICT flows имеют автоматическую traceability;
- Dashboard содержит реальные data;
- Opportunity и GitHub pipelines работают для linked/unlinked users по PRD;
- decision escalation реально достигается;
- документация не противоречит OpenAPI и коду;
- backend может обоснованно считаться shipped.

---

# 6. Итоговая матрица выполнения

| Порядок | Фаза | Основной результат | Блокирует |
|---:|---|---|---|
| 1 | 1.1 Configuration | Единый Settings API | Все imports и deploy |
| 2 | 1.2 Dependencies | FastAPI routers собираются | Запуск API |
| 3 | 1.3 Package layout | Workers работают в Docker | Async pipelines |
| 4 | 1.4 AI adapter | Поддерживаемый Gemini/ADK client | GitHub analysis |
| 5 | 1.5 Firestore SDK | Queries и transactions выполняются | Profiles, skills, observations |
| 6 | 2.1 Event envelope | Publisher и worker говорят на одном языке | GitHub pipeline |
| 7 | 2.2 Idempotency | Нет duplicate effects | Надёжность Pub/Sub |
| 8 | 2.3 Extractors | Все GitHub events содержательны | Полнота анализа |
| 9 | 2.4 Assessment/escalation | Правильные skills и decisions | Product correctness |
| 10 | 3.1–3.7 API alignment | Frontend и backend имеют один контракт | Интеграция frontend |
| 11 | 4.1–4.6 Security/deploy | Безопасный воспроизводимый Cloud Run | Production readiness |
| 12 | 5.1–5.4 Semantics/performance | Полное поведение PRD | UX и NFR |
| 13 | 5.5 E2E | Доказанный пользовательский flow | Release confidence |
| 14 | 5.6 Docs/tracker | Shipped отражает реальность | Завершение remediation |

# 7. Финальное определение готовности

Backend можно считать восстановленным только если одновременно выполнены следующие условия:

1. FastAPI и workers запускаются в Docker без import/configuration errors.
2. Signed GitHub webhook создаёт ровно одну observation, один skill update и одну decision.
3. Повторная доставка того же event не создаёт повторных side effects.
4. FastAPI-generated OpenAPI совпадает с каноническим `openapi.yaml`.
5. Telegram и Scheduler endpoints защищены и fail-closed.
6. Пользователь без Telegram всё равно получает observations и decisions.
7. Dashboard возвращает реальные, а не mock data.
8. Все исправленные defect tests переведены из `xfail` в passing.
9. Container smoke, emulator integration и основные staging E2E проходят.
10. Backend tracker и глобальный tracker отражают фактический статус, а не только завершение написания файлов.
