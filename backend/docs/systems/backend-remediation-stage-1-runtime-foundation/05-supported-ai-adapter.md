# Фаза 1.4 — supported AI adapter

## Цель

Удалить неподдерживаемый `google.antigravity`, ввести внутренний AI boundary и обеспечить validated GitHub analysis без реальных Gemini calls в unit tests.

## Проверенное SDK основание

В текущем окружении установлен Google ADK 2.7.1. Он предоставляет `google.adk.agents.Agent`/`LlmAgent`, Runner и Pydantic-compatible output schema; модуля `google.antigravity` нет. Окончательная версия фиксируется только после Python 3.11 compatibility gate фазы 1.0.

## Архитектурное решение

- Business/worker layer зависит от внутреннего analyzer interface.
- Google ADK types остаются внутри infrastructure adapter.
- Input и output являются Pydantic domain models.
- Output отдельно содержит proficiency assessment 0..10 и significance score 1..10.
- Retries ограничены, классифицированы и применяются только к transient SDK failures.
- Malformed/partial output не создаёт observation или skill update.

## Scope работ после approval

1. Зафиксировать поддерживаемый ADK construction/execution path для locked SDK version.
2. Определить typed GitHub analysis request/context без зависимости от Pub/Sub envelope этапа 2.
3. Определить strict result model: summary, concept, sentiment, proficiency assessment и significance.
4. Ввести analyzer port и ADK adapter/factory.
5. Инкапсулировать Runner/session/event parsing внутри adapter.
6. Передавать model configuration и client/runner factory через Settings/DI.
7. Мигрировать GitHub analyzer off `google.antigravity`.
8. Убрать module-level model/client construction из Chat и Opportunity analyzers; их product semantics не переписывать.
9. Добавить safe logging: latency, model identifier, outcome/error class без source content и secrets.
10. Ограничить prompt/input size на adapter boundary либо явно зафиксировать follow-up task, если это относится к этапу 4.

## Затрагиваемые файлы

- `ai/agent.py` либо его замена на adapter modules;
- `ai/analyzers/github_analyzer.py`;
- `ai/analyzers/opportunity_analyzer.py`;
- `ai/chat_agent.py`;
- `ai/prompts.py` без изменения product intent;
- новые AI domain/port modules;
- `workers/github_worker.py` только для injection и нового result contract;
- requirements/constraints;
- AI unit и import tests.

## Error model

- Validation error: terminal, no retry, no partial business writes.
- Authentication/configuration error: terminal, sanitised and surfaced at startup/call boundary.
- Timeout/rate limit/service unavailable: bounded retry с backoff/jitter.
- Exhausted retry: typed analyzer-unavailable result/exception для обработки worker в этапе 2.
- Prompt/content не логируется целиком.

## Tests

- adapter import с locked SDK;
- valid structured result;
- distinction between proficiency and significance;
- boundary values и rejection out-of-range;
- invalid JSON/schema and missing fields;
- timeout, retryable failure, retry exhaustion и terminal failure;
- fake runner/client proves zero network usage;
- no business write when analyzer fails;
- unsupported import string отсутствует во всём backend runtime.

## Acceptance criteria

- `google.antigravity` полностью удалён.
- GitHub analyzer использует supported ADK API behind internal interface.
- SDK client/runner заменяется без monkeypatching global objects.
- Structured output проходит Pydantic validation до передачи worker.
- AI import xfail заменён meaningful passing tests.
- Chat/Opportunity import не создаёт model clients.

## Не входит

- Полная унификация chat tools/session history.
- GitHub event extractors.
- Business retry/ack policy Pub/Sub.
- Изменение model name без отдельного product/deployment решения.

## Rollback boundary

Старый unsupported implementation удаляется в том же commit, где новый adapter и tests становятся зелёными; dual runtime paths не поддерживаются.

