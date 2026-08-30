# Фаза 1.0 — baseline and contract freeze

## Цель

Создать воспроизводимую точку отсчёта для Python 3.11/Docker и точную карту дефектов этапа 1 до любых runtime изменений.

## Почему фаза обязательна

Локальное окружение использует Python 3.14, Dockerfile — Python 3.11, а direct dependencies имеют только нижние границы. Без freeze невозможно отличить исправление кода от случайного изменения SDK и доказать воспроизводимость результата.

## Scope работ после approval

1. Зафиксировать baseline test report: количество passed/xfail/warnings и принадлежность каждого xfail remediation stage.
2. Создать stage-1 defect matrix: symptom, root cause, affected entrypoint, owner phase, regression test и exit criterion.
3. Разрешить зависимости в clean Python 3.11 environment и проверить совместимость Google ADK, google-genai, Firestore, Pydantic Settings, FastAPI и Firebase Admin.
4. Выбрать воспроизводимый dependency artifact: exact Python 3.11 constraints/lock, который реально использует Docker build.
5. Зафиксировать generated OpenAPI snapshot только как drift detector; изменение public schemas в этапе 1 запретить.
6. Разделить smoke tests на import-only и startup/lifespan, чтобы import test никогда не запускал внешние сервисы.
7. Описать commands и environment contract для local и CI verification.

## Предполагаемые файлы

- `requirements.txt`;
- `requirements-dev.txt`;
- новый Python 3.11 constraints/lock artifact;
- `Dockerfile` только для подключения lock artifact, без изменения runtime architecture;
- `tests/test_startup_and_contract_regressions.py`;
- новые focused tests/fixtures baseline при необходимости;
- документация текущего плана.

## Test design

- clean dependency resolution выполняется на Python 3.11;
- installed-version audit сохраняется как CI artifact/log;
- baseline suite воспроизводит 70 passed и 26 known xfail до исправлений либо документирует осознанное расхождение;
- OpenAPI snapshot строится только после test-safe dependency override;
- никакой test не читает developer `.env` или ADC.

## Acceptance criteria

- Каждому дефекту этапа 1 соответствует владеющая фаза и regression test.
- Docker build больше не зависит от плавающего набора transitive SDK versions.
- Канонический runtime явно определён как Python 3.11.
- Изменения контрактов этапов 2–5 отделены от текущего scope.
- Baseline report не содержит секретов или credential paths.

## Не входит

- Исправление imports, settings, ADK или Firestore.
- Запуск реальных GCP services.
- Изменение public API.

## Gate для следующей фазы

Фаза 1.1 начинается только после успешной clean install проверки dependency set на Python 3.11.

