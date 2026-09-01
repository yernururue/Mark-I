# Backend staging/production rollout — plan

> **Status:** in-progress  
> **Created:** 2026-09-01  
> **GCP project:** `mark-i-506218`  
> **Primary region:** `us-central1`  
> **Firestore database:** `mark-i` (`europe-west1`)  
> **Safety rule:** trackers are updated only after the complete rollout succeeds

## Goal

Deploy the Mark-I backend to production-named Cloud Run services through a controlled staging validation window, prove the complete asynchronous flows, then activate the production scheduler without changing `frontend/`, tests, xfails, or the shipped correctness-hardening system.

## Scope

- Cloud Build, Artifact Registry, Cloud Run, Pub/Sub, Secret Manager, Firestore indexes, IAM, and Cloud Scheduler in project `mark-i-506218` only.
- Backend deployment configuration and narrowly scoped production-safety fixes needed for rollout.
- Synthetic staging E2E for API, GitHub, Telegram, opportunity collection, idempotency, and both Pub/Sub push workers.
- A sanitized acceptance report and tracker synchronization after every rollout gate passes.

## Non-goals

- No changes under `frontend/`.
- No test deletion, weakening, or `xfail` changes.
- No secret value may be printed, persisted in repository files, or included in the acceptance report.
- No removal of broad legacy IAM grants without a separate explicit authorization.
- No modification of the shipped `backend-correctness-hardening` plan.

## Rollout stages and gates

| Stage | Purpose | Exit gate |
|---|---|---|
| 0 | Plan, goal, and immutable baseline | Separate plan exists; worktree and production baseline recorded |
| 1 | Deployment hardening | Backend tests pass; image/runtime config and logging are production-safe |
| 2 | GCP foundation | Dedicated service accounts, least-privilege IAM, secrets, registry, and indexes are ready |
| 3 | Bootstrap deployment | Cloud Build succeeds; all three Cloud Run revisions are healthy |
| 4 | Staging E2E | Both push paths and all specified API/business flows pass with idempotency evidence |
| 5 | Production promotion | Synthetic data is removed and the authenticated daily scheduler is active |
| 6 | Acceptance and shipping | Sanitized report exists; trackers agree; plan is shipped to `systems/` |

Potentially dangerous or externally visible transitions require a user confirmation that lists the exact targets immediately before execution:

1. IAM bindings and service-account impersonation grants.
2. Cloud Build deployment and Telegram webhook registration.
3. Existing Pub/Sub subscription conversion from pull to authenticated push.
4. Synthetic Firebase/Firestore cleanup.
5. Recurring Cloud Scheduler activation.

## Fixed rollout parameters

- API service: `mark-i-api`
- GitHub worker: `mark-i-github-worker`
- Opportunity worker: `mark-i-opportunity-worker`
- Topics: `github-events`, `opportunity-collect`
- Subscriptions: `github-events-sub`, `opportunity-collect-sub`
- Frontend origin substitution: `https://mark-i-506218.web.app`
- Telegram bot username: `mark1_dev_bot`
- Scheduler: daily at `09:00` in `Asia/Almaty`
- Container registry: Artifact Registry in `us-central1`
- Runtime identities: one dedicated service account per Cloud Run service

## Work breakdown

1. [Initialization and baseline](01-initialization-and-baseline.md)
2. [Deployment hardening](02-deployment-hardening.md)
3. [GCP foundation and secrets](03-gcp-foundation-and-secrets.md)
4. [Bootstrap Cloud Build deployment](04-bootstrap-deployment.md)
5. [Staging end-to-end acceptance](05-staging-e2e.md)
6. [Cleanup and production promotion](06-production-promotion.md)
7. [Acceptance report and shipping](07-acceptance-and-shipping.md)

## Definition of done

- All three Cloud Run services have healthy revisions in `us-central1`; API is public and workers remain private.
- Authenticated Pub/Sub push reaches both private workers and retries remain bounded.
- All six named secrets exist and only intended runtime identities can access them.
- All composite indexes from `backend/firestore.indexes.json` are ready.
- GitHub valid-HMAC and duplicate-delivery scenarios prove one business effect.
- Telegram link/private-update/unlink and linked/unlinked opportunity scenarios pass.
- The scheduler calls the protected opportunity trigger with a secret header without revealing its value.
- The acceptance report contains sanitized commands, resource status, E2E evidence, and residual risks.
- Only then are both trackers updated and this plan moved to `backend/docs/systems/`.
