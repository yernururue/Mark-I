# Task 09 — Acceptance, contracts and shipping

## Findings

R-01, R-04 and the final proof for every finding in the parent plan.

## Changes

- Run the complete suite from a clean locked Python 3.11 environment; keep dependency lock/check evidence.
- Run focused race, retry, duplicate-delivery, shared-repository, group-chat, cursor-tie and legacy-migration scenarios against the Firestore Emulator.
- Build the production Docker image and smoke-test app plus every worker import/startup and `/health` without developer credentials.
- Run deep OpenAPI parity and validate YAML/JSON, index configuration, documentation links and tracker consistency.
- Write `backend/docs/reports/2026-08-30-backend-correctness-hardening-acceptance.md` with exact commands, versions, results and any honest residual limitations.
- Update `openapi.yaml`, `docs/API.md`, `docs/FIRESTORE.md`, `docs/EVENTS.md`, `backend/TRACKER.yaml` and `docs/TRACKER.yaml` to one shipped state.
- Compile the system `README.md`, move the completed plan to `backend/docs/systems/backend-correctness-hardening/`, and preserve diagrams/task records.

## Required gates

1. `pip check` passes in the locked Python 3.11 environment.
2. Complete pytest suite passes with zero unexpected skip/xfail; the four known xfails are ordinary passing tests.
3. Firestore Emulator integration suite passes, including true transaction contention and rollback.
4. Docker build and credential-free runtime smoke tests pass.
5. Generated OpenAPI is deeply equivalent to the canonical contract for the supported surface.
6. No real GitHub, Telegram, Gemini, Firebase, Pub/Sub or Firestore production call occurs in tests.
7. `git diff --check`, YAML and JSON validation pass; no file under `frontend/` changed.
8. Acceptance report maps every F/R/X ID to implementation and passing evidence.

## Dependencies

Tasks 01–08.
