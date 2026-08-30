# Backend remediation Stage 3 — API and Firestore contracts

**Shipped:** 2026-08-29

Stage 3 established `openapi.yaml` as the canonical REST contract and aligned the FastAPI schema, Pydantic models, routers, services, Firestore schema and contract documentation.

## Delivered

- Contract parity tests compare canonical and FastAPI-generated paths, methods, request/response shapes and critical public schemas.
- Chat has the documented request/response names, bounds, persisted IDs, unified channel-aware history and stable cursors.
- Observations support source/concept filtering and duplicate-free cursor pagination.
- Telegram links return the documented data, consume codes transactionally, retain separate Telegram user/chat IDs and unlink idempotently through the service layer.
- Dashboard consumes persisted skills, observations and decisions; decision records use documented policy fields and delivery status.
- Profiles use free-form 1..500-character goals and do not duplicate `/skills`.
- API failures use one documented JSON error envelope.

## Verification

On locked Python 3.11 dependencies, the focused suite reported `75 passed`; the complete backend suite reported `145 passed, 4 xfailed`. The remaining xfails are intentional Stage 4/5 work. See [acceptance report](../../reports/2026-08-29-backend-remediation-stage-3-acceptance.md).

## Source tasks

1. `01-canonical-openapi-and-errors.md`
2. `02-chat-and-observations.md`
3. `03-telegram-dashboard-decisions-profile.md`
4. `04-acceptance-and-shipping.md`

