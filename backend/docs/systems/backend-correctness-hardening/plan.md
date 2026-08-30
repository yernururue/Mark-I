# Backend correctness hardening — plan

> **Status:** shipped  
> **Created:** 2026-08-29  
> **Source:** independent review of backend remediation Stages 1–3  
> **Approval gate:** implementation starts only after user confirmation

## Goal

Remove every confirmed backend defect found by the independent Stage 1–3 review, close the associated correctness and deployment risks, and prove the result on locked Python 3.11 dependencies, the production Docker layout, and the Firestore Emulator without touching `frontend/`.

## Scope

- `backend/` runtime, services, workers, API routes, tests and deployment configuration.
- Canonical shared contracts: `openapi.yaml`, `docs/API.md`, `docs/FIRESTORE.md`, `docs/EVENTS.md`, `docs/TRACKER.yaml`.
- Stage 1–3 system documentation and a new acceptance report when implementation ships.
- The four currently strict-xfailed security/deployment behaviours because the goal is a working backend, not merely a green Stage 1–3 subset.

## Non-goals

- No changes under `frontend/`.
- No weakening or deletion of tests and no conversion of a failing test into `xfail`.
- No use of production credentials or mutation of production GCP, GitHub, Telegram or Firestore state during tests.
- No claim of exactly-once delivery across Telegram's external API. The implementation must instead expose and test an explicit, honest delivery state machine.

## Correctness invariants

1. Importing any app, router, worker or AI module creates no external client and needs no credentials.
2. A logical GitHub activity is attributed only to the Mark-I user who performed it; duplicate repository hooks or webhook deliveries cannot multiply business effects.
3. Observation, skill and decision effects use immutable analysis input and deterministic IDs. A retry cannot reinterpret a partially applied event.
4. Firestore owns atomic state transitions. External sends happen through a durable delivery record with explicit `pending`, `sending`, `sent`, `failed`, `suppressed` or `unknown` status.
5. Telegram user identity and Telegram chat destination are separate. One Telegram identity cannot silently control multiple Mark-I accounts, and group chats cannot leak private profile data.
6. `openapi.yaml` is the source of truth for paths, security, validation, response schemas and the common JSON error envelope.
7. Every dashboard, decision and history field is derived from persisted data; no request-time mock or fabricated timestamp is returned.
8. Cursor order is total and stable: the same ordered timestamp plus document ID is used for both serialization and `start_after` traversal.
9. Every public trigger is authenticated fail-closed and every retryable ingress has a durable idempotency key.

## Finding traceability

| ID | Severity | Finding | Planned task |
|---|---:|---|---|
| F-01 | P0 | ADK runner receives a plain string and every GitHub analysis nacks | 01 |
| F-02 | P1 | Shared repositories create N² fan-out and misattribute teammate activity | 02, 04 |
| F-03 | P1 | Retry after a partial skill write recomputes a different decision | 04 |
| F-04 | P1 | GitHub Telegram delivery targets user ID, ignores failure and leaves decision pending | 04, 05 |
| F-05 | P1 | Telegram identity is not unique; group-chat routing uses chat ID as identity | 05 |
| F-06 | P1 | Generated FastAPI OpenAPI is materially different from the canonical contract | 06 |
| F-07 | P1 | Proficiency is inferred without code and invalid/blank concepts can partially persist | 01, 03 |
| F-08 | P1 | Legacy decisions crash Dashboard because migration/read compatibility is absent | 07 |
| F-09 | P2 | Telegram updates are not idempotent and raw AI replies can be lost/misrendered | 05 |
| F-10 | P2 | Framework 404/405 responses bypass the common error envelope | 06 |
| F-11 | P2 | Dashboard fabricates trend/lastUpdated and reports stale streaks as current | 07 |
| F-12 | P2 | Firestore and event documentation describes schemas/semantics the code does not implement | 07 |
| F-13 | P2 | Profile creation is check-then-set; concurrent creates overwrite and whitespace passes | 06 |
| R-01 | Risk | In-memory Firestore transactions do not model conflicts, rollback or retries; indexes are unversioned | 07, 09 |
| R-02 | Risk | Environment validation and DI are partial and bypassable | 01, 06 |
| R-03 | Risk | Concurrent web/Telegram turns can interleave and reorder | 08 |
| R-04 | Risk | Trackers and acceptance status contradict shipped state | 09 |
| R-05 | Risk | Link codes are non-cryptographic and collision overwrite is possible | 05 |
| X-01 | Known xfail | Public opportunity trigger | 08 |
| X-02 | Known xfail | Telegram webhook secret is optional/fail-open | 05 |
| X-03 | Known xfail | Opportunity processing skips users without Telegram links | 08 |
| X-04 | Known xfail | Cloud Build omits required runtime configuration and secrets | 08 |

## Work breakdown

1. [Runtime and AI contract](01-runtime-and-ai-contract.md)
2. [GitHub ingress and actor attribution](02-github-ingress-and-attribution.md)
3. [GitHub evidence and assessment](03-github-evidence-and-assessment.md)
4. [Durable GitHub effects and decisions](04-durable-effects-and-decisions.md)
5. [Telegram identity, updates and delivery](05-telegram-identity-and-delivery.md)
6. [Canonical API, errors and profile](06-api-errors-and-profile.md)
7. [Firestore schema, migration and dashboard](07-firestore-dashboard-and-migration.md)
8. [Chat, opportunities and deployment](08-chat-opportunities-and-deployment.md)
9. [Acceptance, contracts and shipping](09-acceptance-and-shipping.md)

See `diagram.excalidraw` for the target runtime flow and `blockers.excalidraw` for the implementation gates.

## Sequencing

```text
01 ──┬──> 03 ──> 04 ──┐
     └──> 06 ──> 07 ──┼──> 09
02 ──────> 03          │
04 ──────> 05 ────────┤
05 + 06 + 07 ──> 08 ──┘
```

Tasks that touch the same persistence invariants stay sequential. Focused tests run after each task; the complete locked suite, emulator integration suite and Docker smoke gates run only in task 09.

## Definition of done

- Every finding and risk in the traceability table is either fixed and covered by a passing test or documented as an unavoidable external-system limitation with an explicit product state and recovery path.
- All four current strict xfails pass as ordinary tests; no new xfails are introduced.
- Locked Python 3.11 install passes `pip check`, focused tests and the complete test suite.
- Firestore Emulator tests demonstrate conflict retry, rollback, cursor ties, uniqueness and concurrent claim behaviour.
- Docker builds and proves app/worker imports plus `/health` without developer credentials.
- Generated FastAPI OpenAPI passes deep semantic parity against `openapi.yaml`.
- `docs/API.md`, `docs/FIRESTORE.md`, `docs/EVENTS.md`, acceptance reports and both backend/global trackers match shipped behaviour.
- The plan is moved to `backend/docs/systems/backend-correctness-hardening/` only after every gate passes.
