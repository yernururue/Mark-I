# Mark-I — API Contract

> **Status:** Draft v1.0  
> **Last updated:** 2026-08-29
> **Canonical source:** `openapi.yaml`  
> **API Version:** v1  
> **Base URL:** `https://<backend-url>/api/v1`

---

## Overview

This document defines the REST API contract between frontend and backend. All endpoints are also defined in [openapi.yaml](file:///Users/macbook/Yernur/projects/Mark-I/openapi.yaml), which is the formal API source of truth.

### Authentication

All `/api/v1/*` endpoints require a Firebase ID token in the `Authorization` header:

```
Authorization: Bearer <firebase-id-token>
```

Exceptions:
- `GET /health` — no auth
- `POST /api/v1/webhooks/github` — HMAC signature validation
- `POST /api/v1/webhooks/telegram` — secret path token validation

### Error Format

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description"
  }
}
```

### Common Error Codes

| HTTP Status | Code | Description |
|------------|------|-------------|
| 401 | `UNAUTHORIZED` | Missing or invalid Firebase token |
| 403 | `FORBIDDEN` | Token valid but access denied |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource already exists |
| 422 | `VALIDATION_ERROR` | Invalid request body |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |

---

## Frontend API Endpoints

### Health Check

---

#### `GET /health`

Health check endpoint. No authentication required.

**Response 200:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-08-19T14:00:00Z"
}
```

---

### User Profile

---

#### `GET /api/v1/me`

Get the authenticated user's profile.

**Authentication:** Required  

**Response 200:**
```json
{
  "uid": "firebase-uid-123",
  "email": "user@example.com",
  "displayName": "Alex Dev",
  "goal": "job",
  "intensity": "normal",
  "language": "en",
  "telegramLinked": true,
  "telegramUsername": "@alexdev",
  "githubConnected": true,
  "githubUsername": "alexdev",
  "createdAt": "2026-08-15T10:00:00Z",
  "updatedAt": "2026-08-19T12:00:00Z",
  "onboardingCompleted": true
}
```

**Response 404:** User profile not found (first sign-in, not onboarded yet)

---

#### `POST /api/v1/me`

Create user profile (during onboarding). Fails if profile already exists.

**Authentication:** Required  

**Request:**
```json
{
  "displayName": "Alex Dev",
  "goal": "job",
  "intensity": "normal",
  "language": "en"
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `displayName` | string | yes | 1-100 chars |
| `goal` | string | yes | Free-form learning goal, 1-500 characters |
| `intensity` | string | yes | `"chill"`, `"normal"`, `"brutal"` |
| `language` | string | no | `"en"`, `"ru"` (default: `"en"`) |

**Response 201:**
```json
{
  "uid": "firebase-uid-123",
  "email": "user@example.com",
  "displayName": "Alex Dev",
  "goal": "job",
  "intensity": "normal",
  "language": "en",
  "telegramLinked": false,
  "githubConnected": false,
  "createdAt": "2026-08-19T14:00:00Z",
  "updatedAt": "2026-08-19T14:00:00Z",
  "onboardingCompleted": true
}
```

**Response 409:** Profile already exists

---

#### `PATCH /api/v1/me`

Update user profile fields.

**Authentication:** Required  

**Request:**
```json
{
  "displayName": "Alex Developer",
  "goal": "stack:golang",
  "intensity": "brutal",
  "language": "ru"
}
```

All fields optional. Only provided fields are updated. If supplied, `goal` is a free-form value of 1-500 characters. Profile responses intentionally do not include `skills`; use `GET /api/v1/skills` for that data.

**Response 200:** Updated user profile (same format as `GET /api/v1/me`)

---

### Dashboard

---

#### `GET /api/v1/dashboard`

Get aggregated dashboard data in a single request.

**Authentication:** Required  

**Response 200:**
```json
{
  "skills": [
    { "name": "recursion", "score": 4.5, "trend": "up", "lastUpdated": "2026-08-19T12:00:00Z" },
    { "name": "testing", "score": 6.2, "trend": "stable", "lastUpdated": "2026-08-18T15:00:00Z" }
  ],
  "recentObservations": [
    {
      "id": "obs-123",
      "source": "github",
      "summary": "Implemented recursive tree traversal in PR #42",
      "concept": "recursion",
      "sentiment": "positive",
      "significanceScore": 7,
      "createdAt": "2026-08-19T12:00:00Z"
    }
  ],
  "recentDecisions": [
    {
      "id": "dec-456",
      "observationId": "obs-123",
      "action": "notified",
      "reason": "Significance 7 >= threshold 5 (normal intensity)",
      "createdAt": "2026-08-19T12:01:00Z"
    }
  ],
  "stats": {
    "totalObservations": 23,
    "totalSkills": 8,
    "streakDays": 5,
    "lastActivityAt": "2026-08-19T12:00:00Z"
  }
}
```

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `observationLimit` | int | 10 | Max recent observations to return |
| `decisionLimit` | int | 5 | Max recent decisions to return |

---

### Skills

---

#### `GET /api/v1/skills`

Get all skills for the authenticated user.

**Authentication:** Required  

**Response 200:**
```json
{
  "skills": [
    {
      "name": "recursion",
      "score": 4.5,
      "trend": "up",
      "observationCount": 5,
      "lastUpdated": "2026-08-19T12:00:00Z"
    },
    {
      "name": "testing",
      "score": 6.2,
      "trend": "stable",
      "observationCount": 3,
      "lastUpdated": "2026-08-18T15:00:00Z"
    }
  ]
}
```

`trend` values: `"up"` (increased in last 3 observations), `"down"` (decreased), `"stable"` (no significant change), `"new"` (fewer than 3 observations)

---

### Observations

---

#### `GET /api/v1/observations`

Get observations for the authenticated user, with pagination and filters.

**Authentication:** Required  

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Max items per page (1-100) |
| `cursor` | string | null | Opaque cursor from the previous response (`createdAt` + document ID tie-breaker) |
| `source` | string | null | Filter by source: `github`, `opportunity`, `chat` |
| `concept` | string | null | Filter by concept name |

**Response 200:**
```json
{
  "observations": [
    {
      "id": "obs-123",
      "source": "github",
      "summary": "Implemented recursive tree traversal in PR #42",
      "concept": "recursion",
      "sentiment": "positive",
      "significanceScore": 7,
      "metadata": {
        "repo": "alexdev/algorithms",
        "event": "pull_request",
        "ref": "PR #42"
      },
      "createdAt": "2026-08-19T12:00:00Z"
    }
  ],
  "nextCursor": "eyJjcmVhdGVkQXQiOiAiMjAyNi0wOC0xOVQxMTowMDowMFoifQ==",
  "hasMore": true
}
```

---

### Chat

---

#### `POST /api/v1/chat`

Send a message to the AI agent. The agent processes the message with full user context and returns a response.

**Authentication:** Required  

**Request:**
```json
{
  "message": "Why did you notify me about that last commit?",
  "channel": "web"
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `message` | string | yes | 1-2000 chars |
| `channel` | string | yes | `"web"`, `"telegram"` |

**Response 200:**
```json
{
  "response": "I notified you because your commit to algorithms/recursion.py showed a significant improvement in recursive thinking...",
  "messageId": "msg-789",
  "agentMessageId": "msg-790"
}
```

**Note:** Both the user message and agent response are automatically stored in Firestore `users/{uid}/messages/`. Frontend can also listen to this collection for realtime updates.

---

#### `GET /api/v1/messages`

Get chat message history.

**Authentication:** Required  

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max messages to return (1-200) |
| `cursor` | string | null | Opaque cursor from the previous response (`createdAt` + document ID tie-breaker) |
| `channel` | string | null | Filter by channel: `web`, `telegram` |

**Response 200:**
```json
{
  "messages": [
    {
      "id": "msg-789",
      "role": "user",
      "channel": "web",
      "text": "Why did you notify me about that last commit?",
      "createdAt": "2026-08-19T14:00:00Z"
    },
    {
      "id": "msg-790",
      "role": "agent",
      "channel": "web",
      "text": "I notified you because your commit to algorithms/recursion.py showed a significant improvement...",
      "createdAt": "2026-08-19T14:00:01Z"
    }
  ],
  "nextCursor": "eyJjcmVhdGVkQXQiOiAiMjAyNi0wOC0xOVQxMzowMDowMFoifQ==",
  "hasMore": true
}
```

---

### GitHub Integration

---

#### `GET /api/v1/github/auth-url`

Get the GitHub OAuth authorization URL to redirect the user to.

**Authentication:** Required  

**Response 200:**
```json
{
  "authUrl": "https://github.com/login/oauth/authorize?client_id=xxx&redirect_uri=xxx&scope=repo&state=xxx"
}
```

---

#### `POST /api/v1/github/callback`

Handle the GitHub OAuth callback. Exchange the authorization code for an access token.

**Authentication:** Required  

**Request:**
```json
{
  "code": "github-oauth-code-xxx",
  "state": "state-token-xxx"
}
```

**Response 200:**
```json
{
  "githubUsername": "alexdev",
  "repos": [
    { "fullName": "alexdev/algorithms", "private": false },
    { "fullName": "alexdev/web-app", "private": true },
    { "fullName": "alexdev/dotfiles", "private": false }
  ]
}
```

**Response 400:** Invalid code or state

---

#### `GET /api/v1/github/repos`

Get list of repos available to connect (already authorized via OAuth).

**Authentication:** Required  

**Response 200:**
```json
{
  "repos": [
    { "fullName": "alexdev/algorithms", "private": false, "connected": true },
    { "fullName": "alexdev/web-app", "private": true, "connected": false },
    { "fullName": "alexdev/dotfiles", "private": false, "connected": false }
  ]
}
```

**Response 400:** GitHub not connected

---

#### `POST /api/v1/github/repos`

Select repos to monitor. Registers/removes webhooks accordingly.

**Authentication:** Required  

**Request:**
```json
{
  "repos": ["alexdev/algorithms", "alexdev/web-app"]
}
```

**Response 200:**
```json
{
  "connectedRepos": ["alexdev/algorithms", "alexdev/web-app"],
  "webhooksRegistered": 2
}
```

---

#### `DELETE /api/v1/github/disconnect`

Disconnect GitHub entirely. Removes webhooks and token.

**Authentication:** Required  

**Response 200:**
```json
{
  "disconnected": true
}
```

---

### Telegram

---

#### `POST /api/v1/telegram/link`

Generate a Telegram link code for the authenticated user.

**Authentication:** Required  

**Response 200:**
```json
{
  "linkCode": "A3X9K2",
  "expiresAt": "2026-08-19T14:10:00Z",
  "botUsername": "mark1_dev_bot"
}
```

**Response 409:** Telegram already linked (use `DELETE /api/v1/telegram/unlink` first)

---

#### `DELETE /api/v1/telegram/unlink`

Unlink the Telegram account.

**Authentication:** Required  

**Response 200:**
```json
{
  "unlinked": true
}
```

---

## Webhook API Endpoints

These endpoints are called by external services, NOT by the frontend.

---

#### `POST /api/v1/webhooks/github`

Receive GitHub webhook events. Validated via HMAC SHA-256 signature.

**Authentication:** `X-Hub-Signature-256` header  
**Content-Type:** `application/json`

**Headers:**
```
X-Hub-Signature-256: sha256=<hmac-signature>
X-GitHub-Event: push | pull_request | pull_request_review | issues | issue_comment | create
X-GitHub-Delivery: <delivery-id>
```

**Request:** Raw GitHub webhook payload (varies by event type)

**Response 200:**
```json
{
  "accepted": true,
  "deliveryId": "delivery-id-xxx"
}
```

**Response 401:** Invalid signature
**Response 422:** Unknown event type or missing required fields

---

#### `POST /api/v1/webhooks/telegram`

Receive Telegram bot updates. Validated via `X-Telegram-Bot-Api-Secret-Token`.

**Authentication:** Secret token in URL path  
**Content-Type:** `application/json`

**Request:** Telegram Update object

**Response 200:**
```json
{
  "ok": true
}
```

---

## Internal / Background Operations

These are NOT HTTP endpoints. They are triggered by Pub/Sub or Cloud Scheduler.

### GitHub Event Processing

- **Trigger:** Pub/Sub message on `github-events` topic
- **Processor:** GitHub worker
- **Actions:** Gemini analysis → observation → skill update → decision policy → notification
- **Idempotency:** Deduplicated by GitHub delivery ID in `processed_events/{deliveryId}`

### Opportunity Collection

- **Trigger:** Cloud Scheduler → Pub/Sub `opportunity-collect`
- **Processor:** Opportunity worker
- **Actions:** Fetch sources → Gemini relevance → observation → decision policy → notification
- **Runs for:** Each user with a configured goal

---

## Endpoint Analysis

### Endpoints from initial proposal — Assessment

| Proposed Endpoint | Status | Notes |
|-------------------|--------|-------|
| `GET /health` | ✅ Kept | Standard health check |
| `GET /api/v1/me` | ✅ Kept | User profile read |
| `PATCH /api/v1/me` | ✅ Kept | User profile update |
| `POST /api/v1/me` | ✅ Added | Create profile during onboarding |
| `GET /api/v1/dashboard` | ✅ Kept | Aggregated dashboard data |
| `GET /api/v1/skills` | ✅ Kept | Detailed skills list |
| `GET /api/v1/observations` | ✅ Kept | With pagination + filters |
| `GET /api/v1/messages` | ✅ Kept | Chat history with pagination |
| `POST /api/v1/chat` | ✅ Kept | Send message to agent |
| `POST /api/v1/telegram/link` | ✅ Kept | Generate link code |
| `DELETE /api/v1/telegram/unlink` | ✅ Added | Missing — needed for re-linking |
| `POST /api/v1/github/connect` | ❌ Replaced | Split into auth-url, callback, repos |
| `GET /api/v1/github/auth-url` | ✅ Added | OAuth flow step 1 |
| `POST /api/v1/github/callback` | ✅ Added | OAuth flow step 2 |
| `GET /api/v1/github/repos` | ✅ Added | List available repos |
| `POST /api/v1/github/repos` | ✅ Added | Select repos to monitor |
| `DELETE /api/v1/github/disconnect` | ✅ Added | Disconnect GitHub |
| `POST /api/v1/webhooks/github` | ✅ Kept | GitHub webhook receiver |
| `POST /api/v1/webhooks/telegram` | ✅ Kept | Telegram webhook receiver |

### Key Changes from Original Proposal

1. **GitHub connect** was a single endpoint — split into full OAuth flow (auth-url, callback, repos, disconnect)
2. **Telegram unlink** was missing — added for re-linking capability
3. **POST /api/v1/me** added for explicit profile creation (onboarding)
4. **Pagination** added to observations and messages (cursor-based)
5. **Dashboard** aggregates skills + observations + decisions + stats in one call
