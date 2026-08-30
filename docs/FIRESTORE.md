# Mark-I — Firestore schema

> **Status:** Current backend contract
> **Last updated:** 2026-08-29
> **Write authority:** backend/Admin SDK only. Client reads are constrained by [firestore.rules](../firestore.rules).

All timestamps are UTC Firestore timestamps. API responses serialise them as ISO 8601 date-times. `openapi.yaml` is the HTTP contract; this document is the storage and state-machine contract.

## User-owned data

### `users/{uid}`

The document ID is the Firebase UID. Required profile fields are `uid`, `email`, trimmed `displayName` (1–100), free-form trimmed `goal` (1–500), `intensity`, `createdAt`, and `updatedAt`.

| Field | Meaning |
|---|---|
| `language` | `en` or `ru`, defaults to `en` |
| `telegramUserId` | Telegram **person** ID, or `null`; never use a chat ID here |
| `telegramChatId` | private destination chat ID, or `null` |
| `telegramUsername` | display-only username, or `null` |
| `githubConnected`, `githubUsername`, `githubUserId`, `connectedRepos`, `webhookIds` | GitHub integration state; OAuth tokens remain in Secret Manager |
| `skills` | current `concept -> score` map (0–10) |
| `skillSignals` | backend-owned metadata per concept: `recentScores` (at most 3), `recentSentiments` (at most 3), `lastUpdatedAt`, `lastActivityId` |

`skills` is not copied into `UserProfile`. `GET /skills` derives its count, timestamp and trend from `skillSignals` and observations. A legacy score without any persisted timestamp/evidence is intentionally omitted rather than presented with a fabricated `now()` value.

### `users/{uid}/observations/{observationId}`

Every observation has `id`, `source` (`github`, `opportunity`, or `chat`), `summary`, `concept`, `sentiment`, `significanceScore` (1–10), `metadata` (map) and `createdAt`.

Newest-first observation pages use the stable tuple `(createdAt DESC, documentId DESC)`. The opaque cursor encodes that exact tuple. A record inserted before an already-issued cursor belongs to a newer logical snapshot and does not appear on later pages; ties neither duplicate nor omit records.

### `users/{uid}/messages/{messageId}`

Messages from web and Telegram share one collection and have `id`, `role` (`user` or `agent`), `channel` (`web` or `telegram`), `text`, and `createdAt`. History is ordered by `(createdAt ASC, documentId ASC)` and uses the same opaque tuple-cursor rule.

### `users/{uid}/chat_turns/{sha256(turnId)}` and `chat_state/active`

`turnId` is an optional client idempotency key (Telegram derives one from `update_id`). A turn stores its immutable prompt/channel, deterministic user/agent message IDs, sequence number, lease and terminal state. `chat_state/active` serializes one model invocation per user across web and Telegram. A completed retry returns the stored response; an expired in-flight turn becomes `unknown`, never automatically re-invoked, because a model provider may already have received it.

### `users/{uid}/decisions/{decisionId}`

Current records use `schemaVersion: 2` and contain:

| Field | Meaning |
|---|---|
| `id`, `observationId`, `createdAt` | identifiers and immutable decision time |
| `action` | policy decision: `notified` or `silent` (not a delivery claim) |
| `significanceScore`, `threshold`, `intensity`, `escalationFlags`, `reason` | deterministic policy input/output |
| `deliveryStatus` | `pending`, `sending`, `sent`, `suppressed`, `failed`, or `unknown` |
| `expiresAt` | optional TTL timestamp for retention |

Legacy documents with `shouldNotify` and an unambiguous `intensityThreshold` of 3, 5, or 7 are read compatibly as v2. `shouldNotify=true` maps to `action=notified` and `deliveryStatus=unknown`; the old row cannot prove delivery. Ambiguous legacy records are excluded from the dashboard and reported by `python backend/scripts/migrate_decisions.py --dry-run`; the migration never guesses an action.

## Backend-only state

### `telegram_link_codes/{sha256(code)}`

One-time six-character codes are returned only by the authenticated API. The plaintext code is never a document ID or stored field. Fields are `uid` and `expiresAt`. Reservation and consumption happen in Firestore transactions; a successful link deletes the code.

### `telegram_identities/{telegramUserId}`

The document ID is the Telegram **sender** ID. It provides the unique ownership index `{uid, telegramUserId, telegramChatId, telegramUsername, updatedAt}`. Linking claims this document, updates the user, and consumes the code in one transaction. Unlink deletes it only if it remains owned by that UID.

### `telegram_updates/{updateId}`

Webhook deduplication state has `state` (`processing`, `retryable`, or `completed`), `leaseUntil`, `attempt`, and `updatedAt`. The webhook claims this document before invoking the handler. A completed delivery is safely ACKed; an active lease returns retryable 503 rather than losing the update.

### `github_repository_hooks/{sha256(repoFullName)}`

One physical GitHub webhook is shared by all subscribers of a repository. It stores the canonical endpoint, GitHub hook ID, normalized repository, and subscriber UIDs. Deleting one user disconnects only that subscriber; the remote hook is removed after the final subscriber leaves.

### `processed_events/{github:activityId:uid}`

This is the logical GitHub activity state machine, not merely a delivery-ID tombstone. It stores `activityId`, audit `deliveryIds`, `userId`, claim `status`/lease/attempt, immutable `prepared` AI analysis, and atomically applied observation/skill/decision effects. Physical redeliveries append their `deliveryId` but do not repeat business effects.

### `collected_opportunities/{eventId}` and `opportunity_effects/{sha256(eventId:uid)}`

`collected_opportunities` records the source item and its first/last collection times. It is deliberately not a per-user deduplication tombstone: the scheduler republishes the source's current window so users who later set a goal can be evaluated.

`opportunity_effects` is the per-user decision boundary. It records an `ignored` relevance result below 7 or an `applied` deterministic observation/decision/outbox effect. The worker reads it before invoking AI on a redelivery, so replaying current source items neither repeats model calls nor creates duplicate product data.

### `delivery_effects/{deliveryId}`

The outbox record contains `activityId`, `uid`, `decisionId`, `telegramChatId`, `status`, attempt/lease timestamps and `lastError`. `sending` leases that expire become `unknown` rather than being automatically resent, because Telegram has no idempotency key.

## Indexes and retention

Declared composite indexes live in [backend/firestore.indexes.json](../backend/firestore.indexes.json): observation filters by `source` and/or `concept` with `createdAt DESC`, and channel-filtered messages with `createdAt ASC`. Firestore appends the document-name tie-breaker required by the cursor queries. Decisions use the default `createdAt DESC` index.

`processed_events`, `opportunity_effects`, `collected_opportunities`, `delivery_effects`, `telegram_updates`, chat-turn state, and expired link codes are backend-only and must not be exposed by client rules. Retention/TTL configuration is deployed infrastructure; no background reader should treat an expired `sending` lease as permission to send another Telegram message.

## Secrets and client access

Firestore never stores GitHub OAuth access tokens, GitHub webhook secrets, Telegram bot tokens, API keys, or service-account keys. GitHub user tokens are referenced by a Secret Manager name. Clients may read only their own `users/{uid}` document and its `observations`, `messages`, and `decisions` subcollections; all writes use backend service layers.
