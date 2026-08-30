# Backend correctness hardening — acceptance report

**Date:** 2026-08-30  
**Scope:** backend remediation Stages 1--3 and their shared API/Firestore/event contracts. No file under `frontend/` was changed.

## Result

All confirmed findings F-01--F-13 and known regressions X-01--X-04 are implemented as ordinary passing tests. The complete locked Python 3.11 suite passed with no xfail. Runtime, Firestore Emulator, canonical OpenAPI and fresh Docker-image gates passed.

## Evidence

| Gate | Command | Result |
|---|---|---|
| Locked dependency integrity | `/tmp/mark-i-stage3-py311/bin/python -m pip check` | `No broken requirements found` |
| Full backend + Firestore Emulator | `firebase emulators:exec --only firestore --project demo-mark-i --config firebase.emulator.json '... python -m pytest -q'` | `215 passed, 3 warnings` |
| Emulator transaction scenarios | same command scoped to `tests/test_firestore_emulator_integration.py` | `2 passed` |
| Canonical contract parity | included in full suite (`test_stage3_api_firestore_contracts.py`) | passed, including deep generated-vs-canonical OpenAPI comparison |
| Static artifact validation | Python `yaml.safe_load` / `json.loads` for OpenAPI, Cloud Build, trackers, emulator and index config | passed |
| Diff hygiene | `git diff --check` | passed |
| Fresh canonical image | `docker build --progress=plain -t mark-i-backend-acceptance:20260830 backend` | passed; 0.56 MB production context |
| Container API smoke | `docker run ... mark-i-backend-acceptance:20260830` then `curl /health` | `200`, `{"status":"ok","version":"1.0.0",...}` |
| Container worker import | `docker run --rm ... python -c 'from app.worker_apps import github_app, opportunity_app'` | `worker-app-imports-ok` |

The three warnings are third-party deprecations from OpenTelemetry metadata, Starlette `TestClient` and Google ADK `BaseAgentConfig`; none is a backend failure.

## Finding closure

| Finding | Accepted implementation / regression evidence |
|---|---|
| F-01, F-07, R-02 | Typed ADK GitHub adapter; strict AI output; lazy role settings and injectable credential-free AI boundaries, including opportunity analysis. `test_runtime_ai_contract.py` |
| F-02, F-03, F-04 | Versioned GitHub activity envelope, actor-qualified fan-out, prepared immutable analysis, transactional effects and durable delivery claims. GitHub PICT/evidence/processed-event tests |
| F-05, F-09, R-05 | Transactional hashed Telegram link codes, one-to-one identity index, private-chat-only interaction, update claim and honest send outcomes. Telegram PICT/webhook tests plus emulator contention test |
| F-06, F-10, F-13 | Canonical OpenAPI parity, common error envelope, constrained requests and create-only profile persistence. Stage-3/profile tests |
| F-08, F-11, F-12, R-01 | Legacy decision migration/read layer, real dashboard derivation, declared indexes, stable cursor tuple and updated storage/event documents. Firestore/dashboard tests plus emulator rollback test |
| R-03 | Durable per-user chat turns serialise web/Telegram model calls, replay completed IDs and stop bounded tool loops. `test_chat_pict.py` |
| X-01 | Scheduler trigger compares a required shared secret in constant time and fails closed. `test_opportunity_trigger.py` |
| X-02 | Telegram webhook requires its configured secret and fails closed. `test_telegram_webhook.py` |
| X-03 | Opportunity effects persist per `(eventId, uid)` independently of Telegram linkage; source replay enables a newly eligible user. `test_opportunity_worker.py`, `test_opportunity_pict.py` |
| X-04 | Cloud Build binds all API secrets/configuration and deploys private Pub/Sub push worker services that listen on Cloud Run's port. `test_worker_push_apps.py`, startup regression test |
| R-04 | This report, system README and both trackers record the shipped state. |

## Deliberate external limitations and deployment prerequisites

- Telegram has no idempotency key. A transport-ambiguous send becomes `unknown` and is never automatically resent; reconciliation must be an explicit operator action.
- Cloud Build requires trigger substitutions `_WEBHOOK_BASE_URL`, `_TELEGRAM_BOT_USERNAME`, `_TELEGRAM_WEBHOOK_URL`, `_FRONTEND_URL` and `_PUBSUB_PUSH_SERVICE_ACCOUNT`. The named Secret Manager versions and both Pub/Sub subscriptions must exist; the build binds the push identity to `roles/run.invoker`.
- The emulator suite uses Admin SDK writes and therefore does not evaluate client Firestore rules. The emulator warns that no rules file is configured; this does not relax production rules or backend write authority.

## No production side effects

Tests used injected AI/Telegram/Pub/Sub/Firestore fakes or Firebase's `demo-mark-i` emulator project. Docker smoke used synthetic development settings and `/health` only. No production GCP, Firebase, GitHub, Telegram or Gemini credential was used.
