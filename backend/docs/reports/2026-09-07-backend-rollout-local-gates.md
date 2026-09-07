# Backend rollout local gates — 2026-09-07

## Outcome

The repository-side deployment-hardening task is complete. Rollout tooling now produces sanitized, fail-closed evidence for the live foundation and bootstrap gates without mutating GCP or reading secret payloads.

Initialization remains in progress because `gcloud` is not installed on the workstation. No IAM binding, service account, secret, index, Pub/Sub subscription, Cloud Run service, webhook, scheduler, or production record was changed.

## Completed controls

- One manifest owns the fixed project, region, service, identity, topic, subscription, secret, registry, and scheduler names.
- Foundation inspection validates the exact project number and lifecycle, required APIs, protected credential mode, regional Docker repository, enabled service accounts, pull or authenticated-push Pub/Sub topology, numeric enabled secret versions, fixed-secret accessors, and declared Firestore indexes.
- Bootstrap inspection validates immutable non-`latest` images, dedicated runtime identities, latest ready revisions, 100% traffic, public API access, private workers, and the approved push invoker.
- Approval rendering enumerates foundation IAM targets and each externally visible rollout transition while marking the document itself as non-mutating.

## Verification

Run from `backend/` with the locked dependencies:

```text
/tmp/mark-i-py311-final/bin/python -m pytest -q
300 passed, 2 skipped, 3 warnings, 26 subtests passed

/tmp/mark-i-py311-final/bin/python scripts/validate_rollout_config.py
rollout-config: ok (12 substitutions, 6 secret bindings, 3 runtime identities, 4 Firestore indexes)
```

The two skips are the existing Firestore Emulator tests because the emulator was not running. Warnings originate from locked third-party dependencies. Frontend files, test expectations, skips, and xfail policy were not changed.

## Next gate

1. Install and authenticate `gcloud` for project `mark-i-506218`.
2. Run the strict read-only foundation inventory with the protected GitHub credential path.
3. Review the generated foundation approval document.
4. Obtain explicit confirmation before applying any IAM or GCP resource mutation.
