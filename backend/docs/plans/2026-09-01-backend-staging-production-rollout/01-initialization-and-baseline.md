# 01 — Initialization and baseline

## Objective

Create the independent rollout workstream and record the immutable pre-change state.

## Tasks

- Create the rollout goal and this phased plan without altering the shipped correctness-hardening system.
- Confirm branch/worktree status and rerun the backend baseline suite.
- Confirm active account, project number, project, region, enabled APIs, and existing resources.
- Record Cloud Run, Pub/Sub, Secret Manager, Firestore index, Scheduler, Artifact Registry, and service-account state without reading secret payloads.
- Confirm the protected local GitHub credential file exists with mode `0600` before secret provisioning.

## Exit criteria

- Baseline is reproducible and no mutation has occurred.
- Missing input or unsafe ambiguity is reported as a blocker.
