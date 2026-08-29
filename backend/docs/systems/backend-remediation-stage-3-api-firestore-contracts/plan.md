# Stage 3 — API and Firestore contracts

## Goal

Make `openapi.yaml` the canonical public REST contract and align FastAPI-generated OpenAPI, Pydantic models, routers, services, Firestore documents and human-readable documentation without touching `frontend/`.

## Scope

- Contract parity tests for the generated FastAPI OpenAPI schema.
- Chat and observation request, response, filtering and cursor-pagination semantics.
- Telegram link/unlink API, transactional one-time codes and separate Telegram user/chat IDs.
- Real dashboard/decision data through services, profile goal validation and unified error envelopes.
- Required updates to `openapi.yaml`, `docs/API.md`, `docs/FIRESTORE.md`, `docs/EVENTS.md` and the global tracker only when the milestone ships.

## Boundaries

Stage 4 security/deployment and Stage 5 performance/E2E work remain out of scope. Tests use only in-memory doubles and test configuration; no production credentials are read or used.

## Architecture

`openapi.yaml` defines HTTP names, validation and response shapes. Pydantic response models expose the same shapes to FastAPI; routers translate HTTP inputs to service calls only; services own Firestore queries/writes. Cursor values encode the ordered timestamp and document ID, making page traversal deterministic where timestamps collide.

## Acceptance gates

1. Canonical and generated OpenAPI have no unexpected path/method/required-field/response-shape differences.
2. Stage 3 PICT and contract tests pass and the relevant strict xfails are converted to ordinary passing tests with real implementations.
3. Focused and complete suites pass on locked Python 3.11 dependencies.
4. YAML/JSON, tracker links and plan artifacts validate.

