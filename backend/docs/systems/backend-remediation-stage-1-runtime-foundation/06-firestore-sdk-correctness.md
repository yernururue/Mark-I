# Фаза 1.5 — Firestore SDK correctness

## Цель

Привести queries и transactions к production Firestore SDK API и защитить skill updates от некорректных данных до side effects.

## Архитектурное решение

- Equality filters создаются через официальный `FieldFilter`.
- Transaction retry wrapper берётся из Firestore module, а client предоставляет transaction instance.
- Skill update выполняет atomic read-modify-write.
- Missing user и invalid inputs имеют явную domain semantics.
- Test fake моделирует используемый production API shape и не добавляет методов, отсутствующих у real client.

## Scope работ после approval

1. Заменить tuple values в `where(filter=...)` на `FieldFilter` во всех services этапа 1.
2. Исправить transaction wrapper SkillService и его injection/test seam.
3. Ввести validation для assessment, weight и concept до создания transaction.
4. Сохранить TRD formula и итоговый score в диапазоне 0..10.
5. Определить missing user как explicit not-found/domain error, а не успешный score 0.
6. Безопасно адресовать skill key, включая concept с точкой/служебными символами, без accidental nested updates.
7. Проверить read/write types и snapshot absence handling.
8. Обновить FakeFirestore: удалить fake-only `client.transactional`, поддержать production filter representation и observable transaction behavior.
9. Заменить implementation-shaped xfail полезными compatibility и behavior tests.
10. Зафиксировать необходимые composite indexes как deployment prerequisite, не выполняя production deploy.

## Затрагиваемые файлы

- `app/services/skill_service.py`;
- `app/services/user_service.py`;
- `app/services/observation_service.py`;
- общие domain errors/validators при необходимости;
- `tests/fakes.py`;
- `tests/test_skill_observation_decision_pict.py`;
- `tests/test_startup_and_contract_regressions.py`;
- emulator/index documentation при необходимости.

## Data invariants

- assessment: finite numeric value 0..10;
- weight: finite numeric value в разрешённом диапазоне, default сохраняет TRD 0.3;
- stored score: finite 0..10;
- missing user не создаётся неявно transaction update;
- transaction retry не применяет бизнес-эффект дважды;
- query filters не собираются из непроверенных operator names.

## Tests

- real SDK exposes expected FieldFilter/module transactional symbols;
- User lookup и Observation concept filter используют production filter shape;
- atomic weighted average для existing/new skill;
- concurrent/retried transaction behavior через faithful mock или emulator-ready test;
- boundary 0/10, invalid negative/>10/NaN/Infinity;
- invalid weight и missing user;
- concept с точкой не создаёт неверную nested map;
- tests не используют ADC или live Firestore.

## Acceptance criteria

- В runtime services нет `where(filter=(...))`.
- В runtime services нет `self._db.transactional`.
- Firestore filter и transaction xfail заменены passing tests.
- Existing PICT weighted-average cases остаются passing.
- Fake больше не предоставляет API, которого нет у production client.
- Firestore schema не изменена.

## Не входит

- Idempotent multi-document GitHub transaction.
- Firestore API/response schema alignment этапа 3.
- Production index deployment этапа 4.

## Rollback boundary

Query migration и transaction migration выполняются отдельными commits; после каждого соответствующий focused suite должен быть зелёным.

