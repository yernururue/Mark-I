# Mark-I — Event and delivery semantics

> **Status:** Current backend contract
> **Last updated:** 2026-08-29

This document describes at-least-once transport and exactly-once business effects. It does not promise exactly-once external Telegram delivery, which Telegram's API cannot provide.

## GitHub activity

1. `POST /api/v1/webhooks/github` verifies `X-Hub-Signature-256`, accepts only supported `X-GitHub-Event` values, and looks up repository subscribers.
2. A repository has one shared remote webhook. The ingress fan-outs one versioned Pub/Sub envelope per eligible owner; the owner must match the GitHub actor (`githubUserId` when available, otherwise login).
3. The published `GitHubEventEnvelope` is `schemaVersion: 2`:

```json
{
  "schemaVersion": 2,
  "deliveryId": "github-physical-delivery-id",
  "activityId": "github:stable-logical-activity-id",
  "eventType": "pull_request",
  "eventAction": "opened",
  "uid": "firebase-uid",
  "repoFullName": "owner/repo",
  "actorLogin": "octocat",
  "actorId": 1,
  "payload": {},
  "receivedAt": "2026-08-29T12:00:00Z"
}
```

`deliveryId` identifies a physical GitHub/Pub/Sub delivery for audit. `activityId` identifies the stable business activity. A redelivery with a different `deliveryId` but the same `activityId` records both IDs and does not create another observation, skill mutation, decision, or outbox message.

4. The worker claims `processed_events/{github:activityId:uid}` with a lease. It collects bounded/redacted code evidence where available, persists strict AI output in `prepared`, then atomically applies the observation, skill signal, decision and delivery outbox record.
5. The decision policy uses **significance** for notification threshold and **proficiencyAssessment** only when code evidence supports a skill update. Supported escalation flags are deterministic: `new_concept`, `skill_regression`, `milestone_reached`, `repeated_error`.
6. Definite retryable work releases the event claim and nacks Pub/Sub. Invalid envelopes and invalid model output are terminal/acknowledged. The immutable prepared analysis is reused on retry.

## Telegram delivery outbox

For a decision requiring a notification, an outbox row is claimed as `sending` before the HTTP request. The outbound destination is `telegramChatId`, never `telegramUserId`.

| Telegram outcome | Durable state | Worker result |
|---|---|---|
| `200` / `ok=true` | `sent` | ACK |
| 429 or 5xx | `failed` | retry event; no business effects repeat |
| definite 4xx / bot not configured | `failed` | ACK; delivery cannot succeed automatically |
| transport failure after request may have left process | `unknown` | ACK; no automatic resend |
| expired `sending` lease | `unknown` | ACK; no automatic resend |

`unknown` deliberately prefers a possible missed message to a possible duplicate notification. A future operator reconciliation flow must make any resend explicit.

## Telegram inbound webhook

`POST /api/v1/webhooks/telegram` requires a configured `X-Telegram-Bot-Api-Secret-Token` and compares it in constant time. If no secret is configured the endpoint fails closed with 503.

The webhook transactionally claims `telegram_updates/{update_id}` before handler side effects:

- completed update → 200 without running the handler again;
- active lease → 503 so Telegram retries rather than losing work;
- handler error → state becomes `retryable`, then the request fails for Telegram retry;
- handler success → state becomes `completed`.

Telegram identity is always `message.from.id`; `message.chat.id` is only a destination. Linking and AI chat are accepted only in a private chat. Group and supergroup messages receive a generic privacy response and never expose a linked profile.

## Chat turns, history and cursors

Web and private Telegram chat write the same `users/{uid}/messages` history. A web caller may supply `turnId`; Telegram uses `telegram:{update_id}`. Firestore claims that turn and a per-user active-turn lease before model invocation. A duplicate completed turn returns its stored IDs and response; an active/failed/unknown turn never starts a second model call. The agent also has a bounded tool-call loop.

Pages are chronological `(createdAt ASC, documentId ASC)`; observation pages are newest-first `(createdAt DESC, documentId DESC)`. Cursors encode both values and therefore do not duplicate equal-timestamp boundaries. New records before a cursor are intentionally outside that cursor's logical snapshot.

## Opportunity flow

Cloud Scheduler calls the protected collection trigger with `X-Scheduler-Secret`; it fails with 503 until the deployment has a configured secret. The trigger publishes the source's current article window to `opportunity-collect` and records source collection separately from user processing. Replaying an item lets a newly eligible user receive an assessment.

The worker evaluates each user with a non-blank goal. A strict relevance result below 7 creates one durable `ignored` effect; relevance 7--10 atomically creates one observation and policy decision per `(eventId, uid)`, independently of whether Telegram is linked. Telegram affects only the delivery row: policy-eligible but unlinked users receive `deliveryStatus=suppressed`. Existing effects are read before AI analysis, so Pub/Sub/source redelivery cannot repeat a business effect or model call.

On Cloud Run the workers receive authenticated Pub/Sub push requests at private services rather than running pull loops: a 2xx response ACKs the message and 503 requests redelivery. The deployment binds the dedicated Pub/Sub OIDC service account as `run.invoker` and updates both push subscriptions after each worker deployment.

## Operational limits

Pub/Sub remains at-least-once with configured dead-letter handling. Firestore transaction retries are expected and every transaction callback is deterministic. Required composite indexes are versioned in `backend/firestore.indexes.json`; deploy them before enabling filtered cursor queries.
