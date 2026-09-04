# Backend rollout hardening checkpoint — 2026-09-04

## Outcome

The repository-side deployment hardening gate is complete and the locked Python 3.11 suite passes. No GCP resource, IAM policy, subscription, webhook, secret payload, scheduler, or production data was changed during this checkpoint.

The rollout remains in progress. Live GCP foundation inspection and every externally visible transition still require the confirmation gates defined in the rollout plan.

## Scope completed

- Artifact Registry images use an overridable immutable `_IMAGE_TAG`, defaulting to the Cloud Build ID.
- All six Cloud Run secret bindings use explicit version substitutions; `latest` is rejected by preflight.
- API and worker services declare the TRD resource envelope: 1 CPU, 512 MiB, 300-second timeout, concurrency 80, minimum 0, maximum 5.
- Cloud Build runs the repository rollout validator before building the image.
- Cloud Build verifies the public API and both authenticated private worker health endpoints after deployment and before the Pub/Sub push gate.
- A read-only GCP inventory command covers the fixed project, region, repository, service accounts, secret metadata, Pub/Sub resources, Cloud Run services, scheduler, and Firestore index states without reading secret payloads.

## Verification evidence

Run from `backend/`:

```text
python3.11 scripts/validate_rollout_config.py
rollout-config: ok (12 substitutions, 6 secret bindings, 3 runtime identities, 4 Firestore indexes)

/tmp/mark-i-py311-rollout/bin/python -m pytest -q
213 passed, 2 skipped, 3 warnings in 14.71s
```

The two skips are the existing Firestore Emulator integration tests because the emulator was not running. There are no test failures or xfails. The three warnings originate from locked third-party dependencies.

`cloudbuild.yaml` also parses successfully as YAML and both rollout scripts compile with Python 3.11.

## Current blockers and non-evidence

- The local workstation does not have the `gcloud` CLI installed, so no claim is made here about current live GCP resource state.
- The Firestore Emulator acceptance gate was not rerun in this checkpoint.
- No Cloud Build was submitted and no Cloud Run revision was deployed.
- Secret existence and versions are not yet verified; this report records names only and contains no secret values.

## Next gate

1. Install/authenticate `gcloud` and run `python3.11 scripts/inspect_rollout_foundation.py` for a read-only baseline.
2. Resolve every reported foundation gap and wait for all four composite indexes to reach `READY`.
3. Present the exact IAM principals, resources, and roles for user confirmation before applying grants.
4. Submit from the repository root with an immutable release tag only after the deployment confirmation gate:

   ```text
   gcloud builds submit . --config=backend/cloudbuild.yaml --substitutions=_IMAGE_TAG=<immutable-release-tag>
   ```

5. Keep `_CONFIGURE_PUBSUB_PUSH=false` through bootstrap deployment. Converting subscriptions to authenticated push remains a separate confirmation gate.
