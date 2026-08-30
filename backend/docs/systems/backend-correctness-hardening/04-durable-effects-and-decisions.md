# Task 04 — Durable GitHub effects and decisions

## Findings

F-03, F-04 (state-machine portion).

## Changes

- Persist immutable validated analysis and the pre-update skill snapshot under the `activityId + uid` event before applying business effects; retain every `deliveryId` only as transport-attempt audit data.
- Assign deterministic IDs to observation, skill mutation, decision and delivery effects; retries reuse the stored payload and never call AI again after analysis succeeds.
- Apply event state, observation, skill and decision transitions in a Firestore transaction with compare-and-set lease ownership.
- Make every effect independently resumable and terminally recorded. An already-applied effect is read, not recomputed.
- Model decisions separately from delivery: `silent` becomes `suppressed`; notify/escalate produces a durable delivery record.
- Use a delivery claim/lease state machine. Record `sent` only from a successful Telegram response, retry definite failures, and record ambiguous post-send timeouts as `unknown` for reconciliation rather than silently duplicating or dropping.
- Ack Pub/Sub only after all required durable effects are terminal; nack retryable failures and terminally record non-retryable failures with diagnostics.

## Acceptance

- A fault injected after each individual write and external boundary converges to one observation, one skill mutation, one decision and no recomputation.
- A retry after skill mutation produces the same original `new_concept`/threshold decision.
- Concurrent consumers cannot both own a live event/effect lease.
- False Telegram results never complete the event or leave a notify decision indefinitely `pending`.
- Lease expiry, retry budget and dead-letter behaviour are covered with a controllable clock.

## Dependencies

Task 03.
