# Backend remediation Stage 2 — acceptance report

**Date:** 2026-08-29  
**Scope:** `backend/` only; GitHub webhook → Pub/Sub → worker pipeline.

## Implemented

- Shared versioned `GitHubEventEnvelope` is serialized by the publisher and validated directly by the worker.
- Webhook publication resolves all matching `connectedRepos` users and publishes an independent message for each uid. An unmatched verified delivery is a logged successful no-op.
- `processed_events/github:{deliveryId}:{uid}` provides transaction-backed ownership, live lease handling, retryable release and completed duplicate ACK.
- Observation, skill and decision records use delivery-derived IDs; skill effects are transactionally recorded in the processed-event record. Telegram dispatch is claimed before send to provide at-most-once dispatch semantics.
- Extractors cover `push`, `pull_request`, `pull_request_review`, `issues`, `issue_comment` and `create`; unsupported valid events complete and ACK without AI/business effects.
- Proficiency is the only value passed to skill updates; significance is the only threshold input to the decision policy. Flags are limited to `new_concept`, `skill_regression`, `milestone_reached` and `repeated_error`.
- The three Stage-2 strict-xfail regressions are now ordinary passing tests. Remaining strict xfails belong to later remediation stages.

## Verification

| Gate | Result |
|---|---|
| Focused Stage-2 and PICT tests | 48 passed |
| Full backend suite | 115 passed, 15 expected xfail, 2 third-party deprecation warnings |
| Python 3.11 syntax check | `python3.11 -m compileall app ai workers telegrambot tests` passed |
| Docker build | `docker build -t mark-i-backend-stage2-verify .` passed |
| Docker Python 3.11 import smoke | envelope, processed-event service, extractor registry and worker imports passed |

The Docker build uses `requirements-py311.lock`. No verification path used production GCP credentials.

## Remaining governance boundary

All four Stage-2 backend tasks are complete. The plan remains `in-progress` pending explicit permission to update the shared global tracker and perform the required system-plan move. No shared files were changed in this stage.
