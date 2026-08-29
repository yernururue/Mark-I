# Mark-I — Firestore Schema

> **Status:** Draft v1.1  
> **Last updated:** 2026-08-29  
> **This document is the database contract between frontend and backend.**

---

## Overview

Firestore is the primary database. All writes go through the backend (Firebase Admin SDK). Frontend reads directly via client SDK with Firestore Security Rules enforcing read-only access.

### Key Principles

1. **Backend owns all writes** — Frontend never writes to Firestore directly
2. **Frontend reads via listeners** — `onSnapshot` for realtime updates
3. **No secrets in Firestore** — GitHub tokens, API keys stored in Secret Manager
4. **User data isolation** — All user data nested under `users/{uid}`
5. **Timestamps** — All timestamps stored as Firestore Timestamps (ISO 8601 in API responses)
6. **Agent attribution** — Agent actions and outputs carry both `agentId` and `runId`
7. **Scoped collaboration** — Agents share outputs by artifact reference or recorded handoff, not unrestricted memory

---

## Collections

### `users/{uid}`

Root user document. Contains profile data and current skill snapshot.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `uid` | string | yes | — | Firebase Auth UID (same as document ID) |
| `email` | string | yes | — | User's email from Firebase Auth |
| `displayName` | string | yes | — | User's display name |
| `goal` | string | yes | — | User's workspace goal; mentor templates may interpret developer-specific goal values |
| `intensity` | string | yes | `"normal"` | Notification intensity: `"chill"`, `"normal"`, `"brutal"` |
| `language` | string | no | `"en"` | Preferred language: `"en"`, `"ru"` |
| `telegramUserId` | number \| null | no | `null` | Telegram user ID (set after linking) |
| `telegramUsername` | string \| null | no | `null` | Telegram username (for display) |
| `telegramChatId` | number \| null | no | `null` | Telegram chat ID (for sending messages) |
| `linkCode` | string \| null | no | `null` | Temporary Telegram link code (6 chars) |
| `linkCodeExpiresAt` | timestamp \| null | no | `null` | Link code expiration time |
| `githubConnected` | boolean | no | `false` | Whether GitHub is connected |
| `githubUsername` | string \| null | no | `null` | GitHub username |
| `githubTokenSecretName` | string \| null | no | `null` | Secret Manager reference for GitHub token |
| `connectedRepos` | array\<string\> | no | `[]` | List of connected repo full names (`owner/repo`) |
| `webhookIds` | map\<string, string\> | no | `{}` | Map of repo → webhook ID for cleanup |
| `skills` | map\<string, number\> | no | `{}` | Skill name → score (0-10). e.g., `{"recursion": 4.5}` |
| `onboardingCompleted` | boolean | no | `false` | Whether onboarding is done |
| `createdAt` | timestamp | yes | — | Account creation time |
| `updatedAt` | timestamp | yes | — | Last profile update time |

**Example Document:**
```json
{
  "uid": "abc123",
  "email": "alex@example.com",
  "displayName": "Alex Dev",
  "goal": "job",
  "intensity": "normal",
  "language": "en",
  "telegramUserId": 123456789,
  "telegramUsername": "@alexdev",
  "telegramChatId": 123456789,
  "linkCode": null,
  "linkCodeExpiresAt": null,
  "githubConnected": true,
  "githubUsername": "alexdev",
  "githubTokenSecretName": "github-token-abc123",
  "connectedRepos": ["alexdev/algorithms", "alexdev/web-app"],
  "webhookIds": {
    "alexdev/algorithms": "12345",
    "alexdev/web-app": "12346"
  },
  "skills": {
    "recursion": 4.5,
    "testing": 6.2,
    "data-structures": 3.0,
    "api-design": 7.1
  },
  "onboardingCompleted": true,
  "createdAt": "2026-08-15T10:00:00Z",
  "updatedAt": "2026-08-19T12:00:00Z"
}
```

**Security:**
- Readable by the owning user (authenticated, `request.auth.uid == uid`)
- Writable only by backend (Admin SDK)
- `githubTokenSecretName` is a reference, NOT the actual token
- `linkCode` is temporary and cleared after use or expiration

**Indexes:**
- Default indexes sufficient (single-field queries)

---

### `users/{uid}/agents/{agentId}`

Stores each user-created agent independently.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | — | Stable agent ID |
| `name` | string | yes | — | User-visible agent name |
| `role` | string | yes | — | Specialist role such as `mentor`, `designer`, or a custom value |
| `template` | string | yes | `custom` | Editable starter template |
| `objective` | string | yes | — | Agent-specific objective |
| `instructions` | string | yes | — | User-authored behavior instructions |
| `tone` | string | no | `normal` | Communication preference |
| `toolGrants` | array\<string\> | no | `[]` | Tools/integrations this agent may use |
| `contextGrants` | array\<string\> | no | `[]` | Workspace sources this agent may read |
| `notificationPolicy` | map | no | `{}` | Agent-specific notification behavior |
| `status` | string | yes | `active` | `active`, `paused`, or `archived` |
| `createdAt` | timestamp | yes | — | Creation time |
| `updatedAt` | timestamp | yes | — | Last configuration update |

---

### `users/{uid}/runs/{runId}`

Durable lifecycle record for one assignment executed by one agent.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | — | Stable run ID |
| `agentId` | string | yes | — | Owning agent |
| `assignment` | string | yes | — | Requested work |
| `status` | string | yes | `queued` | `queued`, `running`, `waiting-for-user`, `completed`, `failed`, or `cancelled` |
| `progress` | string \| null | no | `null` | Latest user-visible progress summary |
| `artifactIds` | array\<string\> | no | `[]` | Outputs produced by this run |
| `parentRunId` | string \| null | no | `null` | Source run when created by an approved handoff |
| `error` | map \| null | no | `null` | Structured failure details |
| `createdAt` | timestamp | yes | — | Queue time |
| `startedAt` | timestamp \| null | no | `null` | Execution start time |
| `finishedAt` | timestamp \| null | no | `null` | Terminal-state time |

---

### `users/{uid}/artifacts/{artifactId}`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | — | Artifact ID |
| `agentId` | string | yes | — | Producing agent |
| `runId` | string | yes | — | Producing run |
| `type` | string | yes | — | Output type such as `report`, `design`, `plan`, or `code-reference` |
| `title` | string | yes | — | User-visible title |
| `content` | string \| map | yes | — | Inline content or storage reference |
| `sharedWithAgentIds` | array\<string\> | no | `[]` | Agents explicitly permitted to read it |
| `createdAt` | timestamp | yes | — | Creation time |

---

### `users/{uid}/observations/{obsId}`

Observations are the core data entity — every meaningful event produces an observation.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | — | Auto-generated document ID |
| `agentId` | string | yes | — | Agent responsible for this observation |
| `runId` | string \| null | no | `null` | Originating run when applicable |
| `source` | string | yes | — | `"github"`, `"opportunity"`, `"chat"` |
| `summary` | string | yes | — | Human-readable summary of the observation |
| `concept` | string | yes | — | Primary concept/skill observed (e.g., `"recursion"`) |
| `sentiment` | string | yes | — | `"positive"`, `"negative"`, `"neutral"` |
| `significanceScore` | number | yes | — | 1-10 significance score (assigned by Gemini) |
| `metadata` | map | no | `{}` | Source-specific metadata |
| `createdAt` | timestamp | yes | — | When the observation was created |

**Source-specific metadata:**

For `source: "github"`:
```json
{
  "repo": "alexdev/algorithms",
  "event": "push",
  "ref": "refs/heads/main",
  "commitCount": 3,
  "deliveryId": "github-delivery-uuid"
}
```

For `source: "opportunity"`:
```json
{
  "sourceUrl": "https://news.ycombinator.com/item?id=12345",
  "sourceName": "Hacker News",
  "title": "Understanding Recursive Data Structures",
  "relevanceScore": 8.5
}
```

For `source: "chat"`:
```json
{
  "channel": "telegram",
  "messageId": "msg-123"
}
```

**Example Document:**
```json
{
  "id": "obs-123",
  "source": "github",
  "summary": "Implemented recursive tree traversal in PR #42. Shows solid understanding of base cases but could improve space complexity.",
  "concept": "recursion",
  "sentiment": "positive",
  "significanceScore": 7,
  "metadata": {
    "repo": "alexdev/algorithms",
    "event": "pull_request",
    "ref": "PR #42",
    "deliveryId": "abc-def-123"
  },
  "createdAt": "2026-08-19T12:00:00Z"
}
```

**Security:**
- Readable by the owning user
- Writable only by backend

**Indexes:**
- Composite: `source` + `createdAt` (descending) — for filtered observation feed
- Composite: `concept` + `createdAt` (descending) — for concept-specific queries

---

### `users/{uid}/messages/{msgId}`

Chat messages from both user and agent, across all channels.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | — | Auto-generated document ID |
| `role` | string | yes | — | `"user"`, `"agent"` |
| `agentId` | string \| null | no | `null` | Addressed/responding agent; null only for unassigned user messages |
| `runId` | string \| null | no | `null` | Associated run |
| `channel` | string | yes | — | `"telegram"`, `"web"` |
| `text` | string | yes | — | Message text content |
| `createdAt` | timestamp | yes | — | When the message was sent |

**Example Document:**
```json
{
  "id": "msg-789",
  "role": "user",
  "channel": "web",
  "text": "Why did you notify me about that last commit?",
  "createdAt": "2026-08-19T14:00:00Z"
}
```

**Security:**
- Readable by the owning user
- Writable only by backend

**Indexes:**
- Default: `createdAt` (ascending) — for chronological message history
- Composite: `channel` + `createdAt` — for channel-filtered history

---

### `users/{uid}/decisions/{decisionId}`

Decision log — records every decision the policy engine makes.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | — | Auto-generated document ID |
| `agentId` | string | yes | — | Agent whose activity was evaluated |
| `runId` | string \| null | no | `null` | Originating run when applicable |
| `observationId` | string | yes | — | Reference to the triggering observation |
| `action` | string | yes | — | `"notified"`, `"silent"` |
| `significanceScore` | number | yes | — | Score from the observation |
| `threshold` | number | yes | — | Threshold that was applied |
| `intensity` | string | yes | — | User's intensity at time of decision |
| `escalationFlags` | array\<string\> | no | `[]` | Any escalation rules that fired |
| `reason` | string | yes | — | Human-readable explanation |
| `createdAt` | timestamp | yes | — | When the decision was made |

**Example Document:**
```json
{
  "id": "dec-456",
  "observationId": "obs-123",
  "action": "notified",
  "significanceScore": 7,
  "threshold": 5,
  "intensity": "normal",
  "escalationFlags": [],
  "reason": "Significance 7 >= threshold 5 (normal intensity)",
  "createdAt": "2026-08-19T12:01:00Z"
}
```

**Security:**
- Readable by the owning user
- Writable only by backend

**Indexes:**
- Default: `createdAt` (descending) — for recent decisions view

---

### `users/{uid}/handoffs/{handoffId}`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | — | Handoff ID |
| `fromAgentId` | string | yes | — | Requesting agent |
| `toAgentId` | string | yes | — | Receiving agent |
| `sourceRunId` | string | yes | — | Run that requested the handoff |
| `targetRunId` | string \| null | no | `null` | Created run after approval |
| `purpose` | string | yes | — | Explicit requested work |
| `artifactIds` | array\<string\> | no | `[]` | Shared inputs |
| `status` | string | yes | `proposed` | `proposed`, `approved`, `rejected`, or `completed` |
| `createdAt` | timestamp | yes | — | Creation time |

---

### `users/{uid}/integrations/{integrationId}`

**ANALYSIS RESULT: NOT NEEDED for MVP.**

GitHub integration state is stored directly on the `users/{uid}` document (`githubConnected`, `connectedRepos`, etc.). A separate subcollection would only be needed if we supported many different integration types (Slack, Discord, etc.), which is out of scope.

---

### `processed_events/{eventId}`

Deduplication collection for idempotent event processing.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventId` | string | yes | Unique event identifier (document ID) |
| `source` | string | yes | `"github"` |
| `userId` | string | yes | UID of the user this event belongs to |
| `processedAt` | timestamp | yes | When the event was processed |

**Document ID format:**
- GitHub: `github-{delivery-id}` (from `X-GitHub-Delivery` header)

**Example:**
```json
{
  "eventId": "github-abc-def-123",
  "source": "github",
  "userId": "abc123",
  "processedAt": "2026-08-19T12:00:00Z"
}
```

**Security:**
- NOT readable by frontend users
- Writable only by backend
- Consider TTL policy (auto-delete after 30 days)

**Indexes:**
- Default index on document ID sufficient

---

## What Must NOT Be Stored in Firestore

| Data | Where to Store | Reason |
|------|---------------|--------|
| GitHub OAuth access tokens | Google Secret Manager | Tokens are secrets, Firestore is readable by client |
| GitHub OAuth client secret | Google Secret Manager | App-level secret |
| Telegram bot token | Google Secret Manager | App-level secret |
| GitHub webhook secret | Google Secret Manager | Used for HMAC validation |
| Firebase service account key | Cloud Run environment | Infrastructure credential |
| Any API keys | Google Secret Manager | Security best practice |

**Pattern:** Store a `secretName` reference in Firestore (e.g., `githubTokenSecretName: "github-token-abc123"`), then resolve the actual secret value from Secret Manager in backend code.

---

## Firestore Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Users can only read their own data
    match /users/{uid} {
      allow read: if request.auth != null && request.auth.uid == uid;
      allow write: if false; // Backend only via Admin SDK
      
      match /observations/{obsId} {
        allow read: if request.auth != null && request.auth.uid == uid;
        allow write: if false;
      }
      
      match /messages/{msgId} {
        allow read: if request.auth != null && request.auth.uid == uid;
        allow write: if false;
      }
      
      match /decisions/{decisionId} {
        allow read: if request.auth != null && request.auth.uid == uid;
        allow write: if false;
      }

      match /agents/{agentId} {
        allow read: if request.auth != null && request.auth.uid == uid;
        allow write: if false;
      }

      match /runs/{runId} {
        allow read: if request.auth != null && request.auth.uid == uid;
        allow write: if false;
      }

      match /artifacts/{artifactId} {
        allow read: if request.auth != null && request.auth.uid == uid;
        allow write: if false;
      }

      match /handoffs/{handoffId} {
        allow read: if request.auth != null && request.auth.uid == uid;
        allow write: if false;
      }
    }
    
    // Processed events — backend only, no client access
    match /processed_events/{eventId} {
      allow read, write: if false;
    }
  }
}
```

---

## Collection Summary

| Collection | Owner | Frontend Read | Frontend Write | Purpose |
|-----------|-------|---------------|----------------|---------|
| `users/{uid}` | Backend | ✅ Realtime listener | ❌ | User profile + skills |
| `users/{uid}/agents/{agentId}` | Backend | ✅ Realtime listener | ❌ | Agent configuration and grants |
| `users/{uid}/runs/{runId}` | Backend | ✅ Realtime listener | ❌ | Concurrent run lifecycle |
| `users/{uid}/artifacts/{artifactId}` | Backend | ✅ Realtime listener | ❌ | Agent outputs |
| `users/{uid}/handoffs/{handoffId}` | Backend | ✅ Realtime listener | ❌ | Auditable agent collaboration |
| `users/{uid}/observations/{obsId}` | Backend | ✅ Realtime listener | ❌ | Observation feed |
| `users/{uid}/messages/{msgId}` | Backend | ✅ Realtime listener | ❌ | Chat history |
| `users/{uid}/decisions/{decisionId}` | Backend | ✅ Realtime listener | ❌ | Decision log |
| `processed_events/{eventId}` | Backend | ❌ | ❌ | Deduplication |
