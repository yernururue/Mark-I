# Backend rollout baseline gate — 2026-09-08

## Outcome

The repository-side Stage 0 baseline gate is now deterministic, provenance-bound, and safe to persist. It distinguishes trustworthy pre-foundation evidence from Stage 2 resource readiness, so resources that have not yet been provisioned do not invalidate the pre-change baseline.

The live GCP inventory is still blocked because `gcloud` is not installed on this workstation. No GCP resource, IAM binding, secret, webhook, subscription, scheduler, or production record was changed.

## Completed controls

- Evidence includes the exact Git commit plus SHA-256 digests for the Dockerfile, Cloud Build configuration, Firestore indexes, Python 3.11 lockfile, and rollout manifest.
- Dirty state is reported as counts only; file paths are not exposed in evidence.
- The `gcloud` SDK version must be present and parseable before authentication or resource inspection begins.
- `--strict-baseline` requires clean provenance, a regular `0600` GitHub credential input, the fixed project identity, and all required APIs, while allowing Stage 2 foundation gaps.
- The exact non-mutating foundation approval target is embedded in the evidence document.
- `--output` creates a new evidence file with mode `0600`, flushes it to disk, and refuses to overwrite existing evidence.

## Verification

Run from `backend/` with the locked Python 3.11 environment:

```text
/tmp/mark-i-py311-final/bin/python -m pytest -q
308 passed, 2 skipped, 3 warnings, 26 subtests passed
```

The two skips remain the existing Firestore Emulator tests because the emulator was not running. The warnings remain in locked third-party dependencies. No frontend file, test expectation, skip, or xfail policy was weakened.

## Next gate

After installing and authenticating `gcloud`, run:

```text
python3.11 scripts/inspect_rollout_foundation.py \
  --strict-baseline \
  --github-credential-file <protected-path> \
  --output <new-owner-only-evidence-path>
```

Review the captured inventory and attached foundation target, then obtain explicit confirmation before any Stage 2 mutation.
