# Task 02 — idempotency, ack/nack and retries

## Objective

Make Pub/Sub's at-least-once delivery safe for each `(deliveryId, uid)` without acknowledging recoverable failures or duplicating downstream effects.

## Design

Use deterministic document ID `processed_events/github:{deliveryId}:{uid}`. A transaction atomically observes/creates a claim with source, delivery ID, user ID, status, started time, attempt/lease metadata and completed time. The implementation must use the Stage-1 supported Firestore transaction API and a faithful fake seam.

| Claim state | Worker action |
|---|---|
| absent | create `processing`, own the event |
| `completed` | ACK immediately; no effects |
| live `processing` lease | NACK or defer according to the defined bounded retry/lease policy; never run concurrently |
| expired `processing` lease | reclaim transactionally and retry |
| terminal invalid/unsupported input | persist terminal disposition where useful, ACK, no effects |

Completion happens only after observation, skill, decision and any required notification outcome have committed. Use deterministic observation/decision/notification-outbox identities or an equivalent transaction/outbox boundary so a process crash between effects and `completed` cannot duplicate an effect. The exact data shape stays within backend implementation scope and must not alter `docs/FIRESTORE.md` in this stage.

## Scope after approval

1. Add a typed processed-event repository/service with injectable clock, transaction runner and retry/lease policy.
2. Parse and validate the envelope before ownership; malformed payload, unsupported schema version and missing required fields are terminal and explicitly ACKed without effects.
3. Classify analyzer/Firestore/Pub/Sub/Telegram errors into terminal versus recoverable, preserving causes and sanitized correlation logging.
4. ACK only completed, completed-duplicate, unsupported, or terminal-invalid messages. NACK recoverable errors after retaining/releasing the claim safely.
5. Ensure deterministic IDs/outbox semantics cover all four business effects, including notification send retries.
6. Define bounded retry/lease constants in configuration/internal policy without starting a Stage-4 DLQ or deployment change.

## Tests

- duplicate delivery after completion ACKs and does not call analyzer/services;
- injected failures before and after each side-effect boundary retry safely;
- concurrent delivery sees a live claim and cannot execute effects twice;
- expired lease recovery works with a fake clock;
- malformed JSON/envelope and unsupported event are terminal ACK paths;
- retryable analyzer/Firestore/Telegram failures NACK; logs omit payloads and secrets;
- existing unrelated strict xfails remain marked; Stage-2 strict xfails are removed only with passing behaviour tests.

## Acceptance criteria

- `processed_events/github:{deliveryId}:{uid}` is present for processed envelopes and stores delivery correlation.
- Duplicate delivery cannot increment skills or send a second notification.
- No missing-uid/silent-skip ACK branch remains.
- Ack/nack behaviour is asserted in all terminal and recoverable cases.

## Rollback boundary

Claim, deterministic-effect/outbox strategy, worker orchestration and regression tests are atomic. Do not land a claim marker that does not yet guard all intended effects.
