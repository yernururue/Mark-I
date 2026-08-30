# Backend correctness hardening

**Status:** shipped on 2026-08-30.

This system closes the independent Stage 1--3 backend remediation review. It keeps all work inside `backend/` plus the shared API, Firestore and event contracts.

## What shipped

- Python 3.11 Docker runtime, lazy role-validated settings and provider-free test seams.
- Versioned GitHub actor fan-out, bounded evidence, immutable prepared analysis and durable effect/delivery state machines.
- Transactional Telegram identity/linking, private-chat safety, update deduplication and explicit Telegram delivery outcomes.
- Deep generated FastAPI/OpenAPI parity, consistent error envelopes, validated profile/chat/observation contracts and real dashboard data.
- Stable Firestore cursors, legacy decision migration, declared indexes and current storage/event documentation.
- Durable cross-channel chat turns, bounded agent tool loops, protected opportunity trigger, per-user opportunity effects and Cloud Run Pub/Sub push workers.

## Verification

The locked Python 3.11 acceptance suite passed `215` tests on the Firestore Emulator; `pip check`, YAML/JSON validation, `git diff --check`, fresh canonical Docker build, API `/health` smoke and worker-app imports passed. See [acceptance report](../../reports/2026-08-30-backend-correctness-hardening-acceptance.md).

## Intentional limits

Telegram deliveries with an ambiguous network outcome stop at `unknown` instead of risking duplicate automatic sends. Cloud Build needs the documented Secret Manager versions, Pub/Sub subscriptions and trigger substitutions before a production deploy.
