# Backend contract inventory and gaps

## Scope and evidence

This is the Task 1 frontend handoff for the repository state at commit `b7b1316`, inspected on 2026-08-30. The route inventory comes from the registered FastAPI v1 router and its response models. No backend file was changed. A live deployment URL is not configured in the frontend environment, so the API owner must confirm that the deployed revision matches this inventory before remote capabilities are enabled.

Frontend local preview remains development-only. Remote mode reads supported documents from Firestore, sends mutations through authenticated REST endpoints, validates every payload at the boundary, and reports unavailable backend contracts instead of creating placeholder remote data.

## Registered backend routes

| Method and route | Deployed repository contract | Frontend alignment | Result |
|---|---|---|---|
| `GET /api/v1/me` | `UserProfile` | Strict profile and integration decoding | Supported, except connected repository count is obtained from `/github/repos` |
| `POST /api/v1/me` | `CreateProfileRequest → UserProfile` | Validated create command and response | Supported for profile creation only; not atomic with first-agent creation |
| `PATCH /api/v1/me` | `UpdateProfileRequest → UserProfile` | Validated update command and response | Supported for `en`/`ru`; frontend `kk` needs backend support |
| `GET /api/v1/github/auth-url` | `{ authUrl }` | Requires a valid HTTPS URL | Supported |
| `POST /api/v1/github/callback` | `{ githubUsername, repos[] }` | Validated callback command and response | Route exists |
| `GET /api/v1/github/repos` | `{ repos[] }` | Validates repo identity/privacy/connection fields | Route exists |
| `POST /api/v1/github/repos` | `{ repos[] } → { connectedRepos, webhooksRegistered }` | Reserved for the repository-selection control | Handler currently references undefined `_get_github_service` |
| `DELETE /api/v1/github/disconnect` | `{ disconnected: true }` | Correct route and validated success response | Handler currently references undefined `_get_github_service` |
| `POST /api/v1/telegram/link` | `{ code }` | Frontend requires `{ code, expiresAt }` | Incompatible; frontend does not trigger the side effect until expiry is returned |
| `DELETE /api/v1/telegram/link` | `{ success: true }` | Corrected frontend route and validated success response | Supported |
| `POST /api/v1/chat` | `{ text } → { text }` | Frontend requires agent/conversation identity and idempotency | Incompatible legacy single-agent contract |
| `GET /api/v1/messages` | `ChatMessage[]` with `id`, `role`, `channel`, `text`, `createdAt` | Frontend requires conversation and agent attribution | Incompatible legacy global history |
| `GET /api/v1/dashboard`, `/skills`, `/observations` | Single-agent-era aggregate resources | Not loaded by the approved roster/chat/run UI | Intentionally unused |

The registered v1 router contains no agent, conversation, run, artifact, or handoff REST routes.

## Required resource contracts

| Resource | Read contract | Mutation contract | Frontend behavior until backend confirmation |
|---|---|---|---|
| Profile | `users/{uid}` or `GET /me`; `uid`, goal, intensity, language, onboarding state, optional identity, validated skill scores | Create/update commands through `/me` | Supported; invalid fields fail the focused profile state |
| Agents | `users/{uid}/agents/{agentId}`; stable identifier, customization, grants, lifecycle, timestamps | List/get/create/update endpoints, including lifecycle changes | Firestore roster/detail reads are supported; create/update/duplicate fail with `backend-contract` |
| Conversations | List/create/select by `agentId`; stable `conversationId`, title, timestamp | Idempotent get-or-create/select | Remote chat fails with `backend-contract`; local preview remains agent-isolated |
| Messages | Conversation-scoped records with `messageId`, `conversationId`, `agentId`, role, content, timestamp, optional `runId` | Send command with `agentId`, `conversationId`, `text`, `clientMessageId` | Legacy global history is rejected rather than mapped into an agent thread |
| Runs | `users/{uid}/runs/{runId}`; owner agent, assignment, lifecycle, output references, timestamps | Start and cancel endpoints returning the updated run | Strict Firestore reads are supported; mutations fail with `backend-contract` |
| Artifacts | `users/{uid}/artifacts/{artifactId}`; `agentId`, `runId`, type, title, content/reference, sharing, timestamp | Backend/runtime publishing only | Strict Firestore reads are supported; frontend never writes directly |
| Handoffs | `users/{uid}/handoffs/{handoffId}`; sender, receiver, source/target run, purpose, artifacts, lifecycle | Approve/reject endpoints | Strict Firestore reads are supported; decisions fail with `backend-contract` |
| Integrations | `/me`, `/github/repos`, and validated integration responses | GitHub connect/callback/repos/disconnect; Telegram link/unlink | Supported routes are decoded; incomplete or defective routes surface explicit errors |

## Blocking backend gaps

1. **BC-01 — Agent management:** add authenticated list/get/create/update routes with stable `agentId`, lifecycle state, grants, schema version, and timestamps.
2. **BC-02 — Isolated conversations:** add list/create/select contracts by `agentId`; every message and chat command/response must carry `conversationId` and `agentId`.
3. **BC-03 — Atomic onboarding:** add one idempotent command that creates or reconciles workspace defaults and the first agent. Add `kk` to the backend language enum if Kazakh remains a supported frontend option.
4. **BC-04 — Runs, artifacts, and handoffs:** add agent-attributed start/cancel and handoff decision endpoints, and publish validated realtime Firestore documents at the TRD paths.
5. **BC-05 — Telegram expiry:** return the server-authored `expiresAt` with the six-character link code. The frontend must not infer server TTL.
6. **BC-06 — GitHub dependency injection:** replace the undefined `_get_github_service` dependency in repository selection and disconnect handlers with the registered GitHub service dependency.
7. **BC-07 — Contract confirmation:** the API owner must confirm route availability, exact response envelopes, Firestore field names, required composite indexes, and the deployed revision before later tasks enable remote controls.

## Frontend enforcement

- `fetchApi` returns `unknown`; a resource decoder must accept a payload before it enters domain state.
- Firestore document IDs are checked against embedded agent/run/artifact/handoff identifiers.
- Local-storage JSON and every stored resource are decoded on read; corrupt preview data is reported rather than cast.
- Local preview is selected only with `NEXT_PUBLIC_DATA_MODE=local` and is forbidden in production.
- Production Firebase builds require `NEXT_PUBLIC_API_URL`; no production fallback selects local data.
- No dashboard markup, stylesheet, asset, navigation item, panel, widget, badge, or layout was changed in Task 1.
