# Backend remediation Stage 3 — acceptance report

**Date:** 2026-08-29
**Scope:** API and Firestore contracts only (`backend/` and the authorised shared contract documents).

## Runtime and locked dependencies

- Python: `3.11.15`
- Lock file: `backend/requirements-py311.lock`
- FastAPI: `0.141.1`
- Pydantic: `2.13.5`
- pytest: `9.1.1`
- PyYAML: `6.0.3`
- Isolated test environment: `/tmp/mark-i-stage3-py311`

## Contract changes accepted

- `openapi.yaml` is checked against FastAPI-generated OpenAPI for every path, HTTP method, request response presence, top-level fields and required fields. Critical nested public schemas (profile, dashboard, decision, observations, chat/messages and Telegram link) are checked separately.
- Chat accepts `message` and required `channel`, enforces 1..2000 characters, returns persisted message IDs, and serves stable, channel-aware history pages.
- Observation pages return `observations`, `nextCursor`, `hasMore`; source/concept filters and timestamp-plus-document-ID cursors prevent boundary duplicates.
- Telegram link responses expose `linkCode`, `expiresAt`, `botUsername`; link consumption is transactional, retains separate user/chat IDs, and unlink is idempotent in `TelegramService`.
- Dashboard aggregates persisted skills, observations and decisions. Decision documents use `action`, `threshold`, `intensity`, `escalationFlags` and `deliveryStatus`.
- Profiles accept a free-form 1..500-character goal and keep skills solely on `/skills`.
- Validation, HTTP and domain failures use the documented `{"error": {"code", "message"}}` JSON envelope.

## Commands and results

```text
/tmp/mark-i-stage3-py311/bin/pytest -q \
  tests/test_stage3_api_firestore_contracts.py tests/test_chat_pict.py \
  tests/test_telegram_pict.py tests/test_profile_and_auth_pict.py \
  tests/test_skill_observation_decision_pict.py
# 75 passed, 2 warnings

/tmp/mark-i-stage3-py311/bin/pytest -q
# 145 passed, 4 xfailed, 3 warnings

python - YAML/JSON artifact validation
# YAML/JSON and Stage 3 plan artifacts: valid

git diff --check
# passed
```

## Xfail and warning accounting

- **Stage 3 strict xfails remaining:** `0`. Each previously expected Stage 3 failure was converted to a normal passing test with a matching implementation change.
- **Total remaining xfails:** `4`, all explicitly deferred Stage 4 or Stage 5 items: scheduler trigger authentication, fail-closed Telegram webhook configuration, opportunities for unlinked users, and deploy-time Cloud Build configuration.
- **Warnings:** one OpenTelemetry metadata deprecation, one Starlette `TestClient`/httpx deprecation, and one Google ADK `BaseAgentConfig` deprecation. None is produced by a Stage 3 contract failure.

## Blockers

None for Stage 3. Stage 4/5 items remain intentionally out of scope and are represented by the four xfails above.
