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

The hardened local gate and its verification are recorded in [the 2026-09-08 checkpoint](../../reports/2026-09-08-backend-rollout-baseline-gate.md).

Once the CLI is installed and authenticated, capture sanitized metadata without reading the credential file or any secret payload:

```text
python3.11 scripts/inspect_rollout_foundation.py \
  --strict-baseline \
  --github-credential-file <protected-path> \
  --output <new-owner-only-evidence-path>
```

`--strict-baseline` requires clean repository provenance, protected credential metadata, the immutable project identity, and required APIs while allowing Stage 2 resources to be absent. After foundation provisioning, rerun with `--strict-foundation` to require those resources and indexes as well. Evidence output is created once with mode `0600`; an existing file is never overwritten.
