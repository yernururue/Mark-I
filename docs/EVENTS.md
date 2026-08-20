# Mark-I — Event Architecture

> **Status:** Draft v1.0  
> **Last updated:** 2026-08-19

---

## Overview

Mark-I uses an event-driven architecture for asynchronous processing. Webhook events and scheduled tasks are decoupled from processing via Cloud Pub/Sub. This ensures:

1. **Fast webhook responses** — Acknowledge webhooks immediately, process async
2. **Retry safety** — Pub/Sub retries failed messages
3. **Idempotency** — Deduplication via `processed_events` collection
4. **Scalability** — Workers can scale independently

---

## Event Flows

### 1. GitHub Activity Flow

```
GitHub (push/PR/review/issue/comment/create)
    │
    ▼
POST /api/v1/webhooks/github
    │
    ├─ 1. Validate HMAC signature (X-Hub-Signature-256)
    ├─ 2. Parse event type (X-GitHub-Event)
    ├─ 3. Identify user by repo → connectedRepos lookup
    ├─ 4. Check deduplication (processed_events/{deliveryId})
    ├─ 5. Publish to Pub/Sub topic: github-events
    └─ 6. Return 200 OK immediately
    
    ▼ (async via Pub/Sub)
    
GitHub Worker (Cloud Run / push subscription)
    │
    ├─ 7.  Receive Pub/Sub message
    ├─ 8.  Double-check deduplication
    ├─ 9.  Load user context (profile, skills, recent observations)
    ├─ 10. Fetch diff/PR content from GitHub API (if needed)
    ├─ 11. Send to Gemini for analysis
    │       → Structured output: concept, proficiency, sentiment, significance
    ├─ 12. Create observation in Firestore
    ├─ 13. Update skill scores (weighted average)
    ├─ 14. Run Decision Policy
    │       → Evaluate significance vs threshold
    │       → Check escalation rules
    │       → Record decision
    ├─ 15. If decision = notify:
    │       → Send Telegram message
    ├─ 16. Write to processed_events/{deliveryId}
    └─ 17. ACK Pub/Sub message
```

#### GitHub Event Details

| GitHub Event | What We Extract | Analysis Focus |
|-------------|----------------|----------------|
| `push` | Commit messages, file diffs | Concepts in code, quality patterns |
| `pull_request` (opened/merged) | PR title, description, diff | Architecture decisions, code organization |
| `pull_request_review` | Review comments | Code review skills, feedback quality |
| `issues` (opened/closed) | Issue title, body | Problem decomposition, project management |
| `issue_comment` | Comment text | Communication, problem-solving |
| `create` (branch/tag) | Branch/tag name | Project structure, workflow |

---

### 2. Opportunity Discovery Flow

```
Cloud Scheduler (cron: every hour for demo)
    │
    ▼
Pub/Sub topic: opportunity-collect
    │
    ▼ (push subscription)
    
Opportunity Worker (Cloud Run)
    │
    ├─ 1. Receive trigger message
    ├─ 2. Fetch content from configured sources
    │       → RSS feeds, APIs, scraping
    ├─ 3. For each user with a configured goal:
    │       ├─ 4. Load user context (goal, skills, recent observations)
    │       ├─ 5. Send items + user context to Gemini
    │       │       → Relevance score (0-10) per item per user
    │       ├─ 6. For items with relevance >= 6:
    │       │       ├─ Create observation (source: "opportunity")
    │       │       ├─ Run Decision Policy
    │       │       └─ If decision = notify: Send Telegram message
    │       └─ 7. Continue to next user
    └─ 8. ACK Pub/Sub message
```

#### Opportunity Sources

> **NOTE:** Sources are TBD. User will provide the final list. Placeholder sources for development:

| Source | Type | Content |
|--------|------|---------|
| TBD-1 | RSS/API | TBD |
| TBD-2 | RSS/API | TBD |
| TBD-3 | RSS/API | TBD |

---

### 3. Telegram Message Flow

```
Telegram User sends message
    │
    ▼
POST /api/v1/webhooks/telegram
    │
    ├─ 1. Validate secret token
    ├─ 2. Parse update type (message / command)
    │
    ├─ If COMMAND (/start):
    │       ├─ 3a. Send welcome message
    │       └─ 4a. Return 200
    │
    ├─ If COMMAND (/link <code>):
    │       ├─ 3b. Look up link code in Firestore
    │       ├─ 4b. Validate code (exists, not expired)
    │       ├─ 5b. Link telegramUserId ↔ uid
    │       ├─ 6b. Clear link code
    │       ├─ 7b. Send confirmation message
    │       └─ 8b. Return 200
    │
    └─ If REGULAR MESSAGE:
            ├─ 3c. Identify user by telegramUserId
            ├─ 4c. If user not linked → send "Please link your account" message
            ├─ 5c. Load user context
            ├─ 6c. Store user message in Firestore (channel: "telegram")
            ├─ 7c. Send to ADK Agent
            ├─ 8c. Store agent response in Firestore (channel: "telegram")
            ├─ 9c. Send response via Telegram Bot API
            └─ 10c. Return 200
```

---

### 4. Web Chat Flow

```
Frontend sends POST /api/v1/chat
    │
    ├─ 1. Verify Firebase ID token
    ├─ 2. Load user context (profile, skills, observations)
    ├─ 3. Store user message in Firestore (channel: "web")
    ├─ 4. Send to ADK Agent with context
    ├─ 5. Receive agent response
    ├─ 6. Store agent response in Firestore (channel: "web")
    └─ 7. Return response to frontend
    
Frontend picks up new messages via Firestore onSnapshot listener
```

---

## Event Definitions

### Event: `github_activity`

| Property | Value |
|----------|-------|
| **Event Name** | `github_activity` |
| **Producer** | GitHub (via webhook) → Backend webhook handler |
| **Consumer** | GitHub Worker (via Pub/Sub) |
| **Pub/Sub Topic** | `github-events` |
| **Payload** | See below |
| **Idempotency** | Deduplicated by `deliveryId` in `processed_events` collection |
| **Retry Strategy** | Pub/Sub automatic retry with exponential backoff (max 3 retries) |
| **Failure Behavior** | Message moves to dead letter topic after max retries. Alert in Cloud Logging. |

**Pub/Sub Message Payload:**
```json
{
  "deliveryId": "github-delivery-uuid",
  "eventType": "push",
  "userId": "firebase-uid-123",
  "repo": "alexdev/algorithms",
  "payload": { /* raw GitHub webhook payload */ },
  "receivedAt": "2026-08-19T12:00:00Z"
}
```

---

### Event: `opportunity_trigger`

| Property | Value |
|----------|-------|
| **Event Name** | `opportunity_trigger` |
| **Producer** | Cloud Scheduler |
| **Consumer** | Opportunity Worker (via Pub/Sub) |
| **Pub/Sub Topic** | `opportunity-collect` |
| **Payload** | See below |
| **Idempotency** | Opportunities are deduplicated by source URL per user |
| **Retry Strategy** | Pub/Sub automatic retry (max 2 retries) |
| **Failure Behavior** | Log error, skip to next schedule. Non-critical. |

**Pub/Sub Message Payload:**
```json
{
  "triggerId": "scheduler-trigger-uuid",
  "triggeredAt": "2026-08-19T12:00:00Z"
}
```

---

### Event: `telegram_update`

| Property | Value |
|----------|-------|
| **Event Name** | `telegram_update` |
| **Producer** | Telegram Bot API (via webhook) |
| **Consumer** | Backend webhook handler (synchronous) |
| **Pub/Sub Topic** | N/A (processed synchronously) |
| **Payload** | Telegram Update object |
| **Idempotency** | Telegram provides `update_id` — can deduplicate if needed |
| **Retry Strategy** | Telegram retries if we don't respond 200 within ~60s |
| **Failure Behavior** | Return 200 to prevent Telegram from retrying. Log error. |

**Design Decision:** Telegram updates are processed synchronously (not via Pub/Sub) because:
1. Telegram expects a fast response (or it retries)
2. Chat responses need low latency for good UX
3. Volume is low (single-user hackathon demo)

---

## Pub/Sub Configuration

### Topics

| Topic Name | Purpose |
|-----------|---------|
| `github-events` | Receives GitHub webhook events for async processing |
| `opportunity-collect` | Receives scheduler triggers for opportunity collection |
| `github-events-dlq` | Dead letter topic for failed GitHub event processing |

### Subscriptions

| Subscription | Topic | Type | Endpoint |
|-------------|-------|------|----------|
| `github-events-sub` | `github-events` | Push | `https://<backend>/internal/workers/github` |
| `opportunity-collect-sub` | `opportunity-collect` | Push | `https://<backend>/internal/workers/opportunity` |
| `github-events-dlq-sub` | `github-events-dlq` | Pull | Manual inspection |

### Push Subscription Config

```yaml
ackDeadlineSeconds: 300        # 5 min for AI processing
messageRetentionDuration: 604800s  # 7 days
retryPolicy:
  minimumBackoff: 10s
  maximumBackoff: 600s
deadLetterPolicy:
  deadLetterTopic: github-events-dlq
  maxDeliveryAttempts: 3
```

---

## Cloud Scheduler Configuration

| Job Name | Schedule | Target | Payload |
|----------|----------|--------|---------|
| `opportunity-trigger` | `0 * * * *` (hourly, demo) | Pub/Sub `opportunity-collect` | `{"triggerId": "<auto>", "triggeredAt": "<auto>"}` |

**Production schedule:** `0 9 * * *` (daily at 9 AM)

---

## Idempotency Strategy

### GitHub Events

1. **Webhook handler:** Check `processed_events/{deliveryId}` before publishing to Pub/Sub
2. **Worker:** Double-check `processed_events/{deliveryId}` before processing
3. **After processing:** Write to `processed_events/{deliveryId}`

This ensures exactly-once processing even with Pub/Sub at-least-once delivery.

### Opportunities

1. Track processed opportunity URLs per user (in observation metadata)
2. Skip opportunities already seen (match by `sourceUrl`)
3. Acceptable to re-notify if opportunity appears in multiple collection runs (edge case)

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| GitHub webhook invalid signature | Return 401, do not process |
| GitHub webhook unknown event type | Return 200 (acknowledge), log and skip |
| Gemini analysis fails | Retry via Pub/Sub. After 3 failures, dead letter queue. |
| Firestore write fails | Retry via Pub/Sub. |
| Telegram send fails | Log error, mark notification as failed. Do not retry. |
| Opportunity source unavailable | Skip source, continue with others. Log warning. |
| User not found for webhook | Log warning, skip. (Repo may have been disconnected.) |
