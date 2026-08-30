# Backend remediation stage 2 — GitHub webhook → Pub/Sub → worker pipeline

Completed 2026-08-29.

## Goal

Make each supported GitHub delivery reach every matching connected user through a versioned envelope, while ensuring that the resulting observation, skill update, decision, and notification occur at most once per `(deliveryId, uid)`.

## Delivered

- Shared versioned `GitHubEventEnvelope`, serialized by the webhook publisher and directly validated by the worker.
- Deterministic `connectedRepos` owner lookup and one independent Pub/Sub message per matching user; an unmatched verified delivery is a successful logged no-op.
- Transaction-backed `processed_events/github:{deliveryId}:{uid}` ownership with leases, retryable release, completed-duplicate ACKs, and deterministic business-effect identities.
- Typed extractors for `push`, `pull_request`, `pull_request_review`, `issues`, `issue_comment`, and `create`; unsupported valid events ACK without AI or business effects.
- Correct Pub/Sub terminal/recoverable handling: malformed or terminal inputs ACK without partial writes, while recoverable infrastructure, AI, Firestore, and Telegram failures NACK for retry.
- Separate AI proficiency and notification significance values: only proficiency updates skills, only significance is evaluated by the decision policy.
- Deterministic, supported escalation flags only: `new_concept`, `skill_regression`, `milestone_reached`, and `repeated_error`.

## Verification

- Focused Stage-2 and PICT tests: 48 passed.
- Full backend suite: 115 passed, 15 expected xfail, 2 third-party deprecation warnings.
- Python 3.11 syntax check: `python3.11 -m compileall app ai workers telegrambot tests` passed.
- Docker build: `docker build -t mark-i-backend-stage2-verify .` passed.
- Docker Python 3.11 import smoke: envelope, processed-event service, extractor registry, and worker imports passed.

Verification used `requirements-py311.lock`, injected fakes, and no production GCP credentials. The three Stage-2 strict-xfail regressions are now ordinary passing tests; remaining strict xfails are owned by later remediation stages.

## System artifacts

- `plan.md` — scope, invariants, sequencing, acceptance criteria, and rollback boundaries.
- `01-event-envelope.md` — shared envelope and recipient fan-out.
- `02-idempotency-and-retries.md` — processed-event claim, deterministic effects, and ACK/NACK policy.
- `03-github-event-extractors.md` — typed extractor registry and context contract.
- `04-assessment-and-escalation.md` — proficiency/significance separation and deterministic escalation.
- `diagram.excalidraw` — pipeline architecture.
- `blockers.excalidraw` — dependencies and scope boundaries.
- `../../reports/2026-08-29-backend-remediation-stage-2-acceptance.md` — detailed acceptance evidence.
