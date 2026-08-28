# Backend remediation stage 2 — GitHub webhook → Pub/Sub → worker pipeline

## Status and approval gate

**Status:** planned. No implementation file, shared contract, deployment configuration or Stage-2 `xfail` may change before explicit user approval. This plan is backend-only.

## Goal

Make every supported GitHub delivery reach each matching connected user through one versioned Pydantic envelope, and ensure its business effects occur at most once: observation, skill update, decision, and, if approved, notification.

This implements remediation-roadmap phases 2.1–2.4 on top of the shipped Stage-1 runtime foundation. It preserves the TRD flow: validate HMAC, publish quickly, asynchronously analyze, record, decide, then acknowledge.

## Scope

1. Introduce a shared `GitHubEventEnvelope` and resolve `connectedRepos` to one Pub/Sub message per uid.
2. Add transaction-backed processed-event ownership, deterministic business-record IDs where needed, classified ack/nack/retry behaviour, and duplicate-notification protection.
3. Replace the partial text switch with typed contexts and extractors for the six registered GitHub webhook event types.
4. Keep AI proficiency assessment separate from notification significance, and calculate only supported deterministic escalation flags.
5. Add focused regression/PICT tests, Python 3.11 and Docker verification, and update this plan's tracker states only after the gates pass.

## Out of scope

- Changes to `openapi.yaml`, `docs/FIRESTORE.md`, `docs/API.md`, `docs/EVENTS.md`, or any other shared file.
- Frontend work, OAuth/repository-selection product changes, webhook security/deployment policy, DLQ provisioning, and Firestore public-schema redesign.
- Stage 3 API/Firestore alignment and Stage 4 production security/deployment work.

## Target flow

`POST /webhooks/github` validates the HMAC and parses JSON. The GitHub service derives `repoFullName`, finds every `users/{uid}` whose `connectedRepos` contains it, and publishes one validated version-1 envelope per uid. An unknown repository is a successful, structured-warning no-op so GitHub does not retry a delivery that has no owner.

The worker validates the same envelope before side effects. It claims `processed_events/github:{deliveryId}:{uid}` transactionally, extracts a typed context, invokes the Stage-1 AI adapter, creates idempotent records, updates proficiency, evaluates significance plus supported flags, sends at most one notification, marks the claim completed, then ACKs. Unsupported event types are logged and ACKed without an AI call or observation. Malformed messages and terminal validation errors are ACKed without partial writes; transient/recoverable failures NACK and retain enough state for a retry.

## Sequencing

| Task | Depends on | Outcome |
|---|---|---|
| 01 event envelope | Stage 1 | Publisher/worker share one versioned data contract and fan-out by uid. |
| 02 idempotency and retries | 01 | At-least-once Pub/Sub cannot duplicate business effects. |
| 03 event extractors | 01 | Each subscribed GitHub event produces non-empty typed analysis input. |
| 04 assessment and escalation | 02, 03 | Skill proficiency and notification significance remain separate. |

Tasks 02 and 03 may be implemented in parallel only after task 01 is green. Task 04 and the final container gate require both.

## Cross-task invariants

- The canonical envelope fields use one Pydantic alias policy; publisher and consumer never hand-convert camelCase/snake_case dictionaries.
- `uid` is required in every published message. Multiple users connected to one repository receive independent envelopes and independent idempotency keys.
- Delivery correlation is preserved in Pub/Sub attributes, structured logs, observation metadata and processed-event records without payload/token logging.
- `processed_events/github:{deliveryId}:{uid}` is the Stage-2 dedupe key. `completed` ACKs; only a valid claimed or expired-lease retry may execute effects.
- ACK happens only after terminal disposition or completed duplicate. Recoverable infrastructure/AI failure NACKs; errors are classified and chained.
- `proficiencyAssessment` (0–10) is the only input to `SkillService.update_skill`; `significanceScore` (1–10) is the only threshold input to `DecisionService`.
- The worker passes only `repeated_error`, `skill_regression`, `new_concept`, and `milestone_reached` to the decision policy.
- A strict xfail is removed only in the same change that makes its real regression test pass. All unrelated remediation xfails remain strict and unchanged.

## Acceptance criteria

1. A valid webhook for a connected repository produces one schema-versioned envelope per matching uid; no-owner delivery returns `200` with a sanitized structured warning.
2. Publisher and worker serialize/validate `GitHubEventEnvelope` directly; missing/unknown-version fields cannot silently become a no-op.
3. Re-delivery does not create another observation, skill update, decision, or Telegram send; terminal duplicate is ACKed.
4. Recoverable errors NACK and retry; invalid/unsupported terminal inputs ACK without business effects; no code path silently ACKs a missing uid.
5. Push, pull request, review, issue, issue comment and create events have focused extractor coverage and meaningful non-empty contexts.
6. PICT escalation cases pass with valid supported flags; proficiency and significance have independent regression assertions.
7. Focused tests and complete backend unit/contract suite pass under the locked Python 3.11 dependencies; Docker build/import and worker processing smoke use fakes and no real GCP credentials.
8. Only after all gates pass: mark tasks/plan in `backend/TRACKER.yaml` following lifecycle rules. No shared tracker update is required until this major milestone is actually completed.

## Rollback boundaries

- Task 01: one atomic contract/fan-out commit; do not leave dual envelope formats.
- Task 02: claim state, deterministic writes, and ack/nack tests travel together; rollback restores the prior worker as a whole rather than partially disabling dedupe.
- Task 03: extractor registry plus tests can roll back independently from the worker infrastructure.
- Task 04: analysis-output use, escalation helper, and PICT tests are one boundary.
- A failed Python 3.11/Docker gate leaves the affected task in progress and is reported as a blocker; it is not solved through `PYTHONPATH`, real credentials, or weakening strict xfails.

## Verification after approval

Run focused envelope/fan-out, worker-idempotency, extractor, and decision PICT tests first; then the backend suite using `requirements-py311.lock`. Build from `backend/` and run import/processing smoke in the Python 3.11 Docker image with injected fake Pub/Sub, Firestore, analyzer and Telegram adapters. Record commands, versions, pass/xfail counts, warnings and any blocker in the Stage-2 acceptance artifact before tracker promotion.
