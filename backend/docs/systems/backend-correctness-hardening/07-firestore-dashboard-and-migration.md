# Task 07 — Firestore schema, migration and dashboard

## Findings

F-08, F-11, F-12, R-01.

## Changes

- Add explicit schema versions and a backward-compatible read/migration path for legacy decisions (`shouldNotify`, `intensityThreshold`) before new-only fields are required.
- Provide an idempotent migration command with dry-run/count/error reporting; do not silently invent an action when legacy data is ambiguous.
- Derive Dashboard skill summaries, trend, counts and `lastUpdated` from persisted observations/skills through services. Remove request-time placeholders and N+1 reads.
- Define current streak precisely: continuous activity ending today or, if product-approved, yesterday; an older historical run returns zero.
- Centralize cursor codecs and queries for messages, observations and decisions using `(orderedTimestamp, documentId)` in both directions, with tie/insert/delete tests and no duplicates.
- Version the required Firestore composite indexes and validate them with the emulator.
- Replace transaction assertions that rely only on the immediate-write fake with emulator tests for conflicts, retries, rollback, uniqueness and lease claims. Keep lightweight doubles only for unit tests.
- Update `docs/FIRESTORE.md` and `docs/EVENTS.md` to match actual IDs, fields, envelopes, retry guarantees and delivery semantics.

## Acceptance

- Legacy, current and mixed decision collections render without 500s and migrate idempotently.
- Dashboard fields equal source data; stale activity does not produce a current streak; no `now()` placeholder is returned.
- Cursor pagination across equal timestamps has no duplicates or omissions under the documented snapshot semantics.
- Emulator conflict/rollback tests would fail against the old fake behaviour and pass against the implementation.
- Index configuration and documentation match every production query and stored schema.

## Dependencies

Task 06; task 04 for event/delivery schemas.

