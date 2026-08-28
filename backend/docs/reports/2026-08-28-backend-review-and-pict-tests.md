# Backend review and PICT test report

> Date: 2026-08-28  
> Scope: backend source, PRD/TRD, API/Firestore/Event contracts, code-review notes, and 83-case PICT design

## Result

The backend tracker marks the MVP as shipped, but the current application is not startable. The supplied review correctly identifies the first four import/runtime blockers, while the code contains additional blockers and substantial drift from `openapi.yaml` and the Firestore/Event contracts.

The added automated suite contains 96 collected cases across all seven PICT flows plus startup and contract regressions:

```text
70 passed, 26 xfailed
```

`xfail(strict=True)` is used only for confirmed defects. A fixed defect becomes an unexpected pass and forces the test marker to be removed, keeping the suite useful as a regression gate.

Run locally:

```bash
cd backend
venv/bin/python -m pip install -r requirements-dev.txt
venv/bin/python -m pytest
```

## Confirmed critical blockers

1. `app.dependencies` does not export `get_db` or `get_current_user_id`, although six routers import them.
2. `app.api.v1.github` references undefined `_get_github_service`; route declaration raises `NameError`.
3. `app.config` does not export `get_settings`, although AI, opportunity, and worker modules import it.
4. Workers import `backend.*`, but the Docker image exposes `app`, `ai`, and `workers` as top-level packages under `/app`.
5. AI analysis imports `google.antigravity`, which is not provided by the installed `google-adk` package or declared dependencies.
6. `SkillService` uses `self._db.transactional`; the production Firestore `Client` has no such method. The review's positive claim that skill updates are atomic is therefore false for the current code.
7. GitHub event producer and consumer use incompatible schemas: publisher writes `deliveryId`/`eventType` and no user ID, while the worker reads `uid`/`event_type`. Valid webhooks cannot reach analysis successfully.
8. GitHub idempotency described in PRD/TRD/EVENTS is not implemented in either the webhook receiver or worker.
9. Services pass tuples through `where(filter=...)`; the installed Firestore client requires a `FieldFilter` object and raises `ValueError` for these queries.

## High-impact product and contract defects

- The public opportunity trigger has no OIDC, shared-secret, or Firebase authentication.
- Telegram webhook authentication becomes optional when `TELEGRAM_WEBHOOK_SECRET` is unset.
- Opportunity processing skips unlinked users before creating an observation or decision, contradicting F12 and PICT case 7.6.
- Only `push` and `pull_request` extract content; review, issue, comment, and create events send empty analysis text despite being documented as supported.
- Chat uses `{text}` and returns `{text}`; OpenAPI requires `{message, channel}` and response/message IDs. Empty and 5000+ character messages are accepted.
- Observation filtering ignores `source`; cursor pagination and `hasMore` are absent.
- Telegram link response and unlink route differ from OpenAPI (`code` vs `linkCode/expiresAt/botUsername`, `/link` vs `/unlink`), and `telegramChatId` is never stored.
- Dashboard and Decision models differ from the documented response/storage schemas.
- Cloud Build supplies only `ENV=production`, while application startup requires multiple settings and secrets.
- Pydantic reports 14 deprecation warnings for `Field(..., env=...)`; this will require migration before Pydantic v3.

## Problems in the supplied documents

- PICT calls the suite end-to-end, but the listed cases do not define emulator/credential setup, external-service isolation, or observable async completion criteria. The new suite automates deterministic unit/contract behavior; live GCP E2E still needs a separate environment.
- Opportunity relevance is `>= 7` in PICT and current code, but `>= 6` in `docs/EVENTS.md`.
- PICT uses `DELETE /telegram/link`; the canonical OpenAPI and `docs/API.md` use `DELETE /telegram/unlink`.
- PICT profile goals are free-form sentences; `docs/API.md` says only `job`, `leetcode`, or `stack:<name>`, while the current Pydantic model accepts any string.
- PICT expects profile responses to contain `skills={}`, but the documented and implemented `UserProfile` response does not expose `skills`.
- The review's `PERF-2` statement is partly stale: `limit_to_last` already has `order_by`. Direct database access and missing pagination remain valid concerns.
- Comparing local Python 3.14 with the documented/Docker Python 3.11 is not itself a defect; compatibility should be verified in the container runtime instead.

## Recommended fix order

1. Restore a clean application import and replace unsupported ADK/Firestore APIs.
2. Define one GitHub Pub/Sub event schema with user resolution and idempotency.
3. Make `openapi.yaml` canonical and align chat, observations, Telegram, dashboard, and decision models/routes.
4. Secure public triggers/webhooks and configure Cloud Run secrets.
5. Implement the missing worker semantics, then convert the corresponding strict `xfail` tests to normal passing tests.
