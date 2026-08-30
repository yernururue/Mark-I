# Task 01 — event envelope and recipient fan-out

## Objective

Define one Pydantic `GitHubEventEnvelope` shared by the webhook publisher and GitHub worker, and resolve a delivery's repository to every eligible user before publication.

## Scope after approval

1. Add the canonical model in the backend domain-model layer with `schemaVersion: Literal[1]`, `deliveryId`, `eventType`, `uid`, `repoFullName`, `payload`, and timezone-aware `receivedAt`.
2. Choose and document one Pydantic validation/serialization alias policy; use model construction plus `model_dump_json()`/`model_validate_json()` at both ends.
3. Add a service-layer repository-owner lookup using the existing `users/{uid}.connectedRepos` data. The lookup must be exact, normalized consistently with stored repository names, deterministic, and testable with Stage-1 Firestore fakes.
4. Build one envelope and one Pub/Sub publish per matching uid. Preserve delivery ID, event type and repository attributes for observability, but treat the envelope body as canonical.
5. Treat a verified delivery for no connected owner as accepted: log a structured, sanitized warning containing delivery ID and repository name and return the existing successful response.
6. Reject malformed payloads and missing repository full names before publish with explicit terminal HTTP behaviour; do not publish an envelope without uid.

## Files expected to change after approval

- `app/models/github.py` or a focused adjacent backend domain module;
- `app/api/webhooks/github.py`;
- `app/services/github_service.py`;
- `workers/github_worker.py` only to consume the model;
- `tests/test_github_pict.py` and new focused contract/fan-out tests.

## Test design

- model round trip, required uid, allowed schema version, timezone-aware received time, and field-name policy;
- receiver → service publisher contract without manual key remapping;
- exactly one message per user for a shared repository, each with its own uid;
- no message and a successful receiver response for an unmatched repository;
- malformed JSON/HMAC failure remain terminal existing boundary behaviour;
- publisher failure is not falsely reported as accepted.

## Acceptance criteria

- Worker can deserialize every publisher output via `GitHubEventEnvelope` directly.
- Every published message includes uid and `schemaVersion=1`.
- Fan-out never mixes one user's ID into another user's envelope.
- Connected-repository matching, unknown-owner handling and publisher failures are regression-tested.

## Not included

Processed-event claims, retries, event-specific extraction, and decisions belong to later tasks.

## Rollback boundary

Commit the model, publisher migration and its consumer compatibility together. No legacy unversioned producer remains after the commit.
