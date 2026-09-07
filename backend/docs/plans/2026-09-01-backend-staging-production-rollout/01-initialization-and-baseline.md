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

## Current blocker

The repository and locked Python 3.11 baselines are reproducible, but the local workstation still has no `gcloud` CLI. Live project inventory therefore remains unverified and this task stays `in-progress`.

Once the CLI is installed and authenticated, capture sanitized metadata without reading the credential file or any secret payload:

```text
python3.11 scripts/inspect_rollout_foundation.py --strict-foundation --github-credential-file <protected-path> --json
```
