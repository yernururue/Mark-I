# 06 — Cleanup and production promotion

## Objective

Remove bounded synthetic state and activate the authenticated daily opportunity trigger.

## Tasks

- Enumerate exact synthetic Firebase UIDs, Firestore paths, and event identifiers.
- Obtain confirmation, then delete only the enumerated synthetic fixtures.
- Present the exact Scheduler job, region, URI, method, schedule, timezone, and retry policy for confirmation.
- Create `opportunity-trigger` with POST, `X-Scheduler-Secret`, `0 9 * * *`, and `Asia/Almaty`.
- Run one manual invocation after cleanup and verify an authenticated successful trigger.

## Exit criteria

- Synthetic state is gone, production data is untouched, and the scheduler is active and healthy.
