# Mark-I — Architecture Decision Records

> **Status:** Draft v1.0  
> **Last updated:** 2026-08-19

---

## Decisions

### ADR-001 — Firebase Auth for authentication

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-001 |
| **Date** | 2026-08-19 |
| **Question** | How do we handle user authentication? |
| **Options** | 1. Custom JWT auth (build from scratch) 2. Firebase Auth 3. Auth0 / Clerk |
| **Decision** | Firebase Auth |
| **Reason** | - Part of the Firebase ecosystem (same project as Hosting and Firestore) — Multi-provider support out of the box (Google, GitHub, Email/Password) — Client SDK handles token refresh, sign-in UI, session persistence — Backend verification via `firebase_admin.auth.verify_id_token()` is trivial — Free tier sufficient for hackathon — Hackathon time constraint favors managed auth |
| **Consequences** | - Tied to Firebase ecosystem — Cannot easily add custom auth providers beyond what Firebase supports — Token format is Firebase-specific (not standard JWT claims) |

---

### ADR-002 — Firestore as primary database

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-002 |
| **Date** | 2026-08-19 |
| **Question** | What database to use for persistent storage? |
| **Options** | 1. Cloud Firestore 2. Cloud SQL (PostgreSQL) 3. MongoDB Atlas |
| **Decision** | Cloud Firestore |
| **Reason** | - Native realtime listeners (`onSnapshot`) enable live dashboard without WebSockets — Same Firebase project as Auth and Hosting — Document model fits our data (user-centric, nested collections) — Serverless, no connection management — Security Rules enforce client-side read access patterns — Free tier for hackathon |
| **Consequences** | - Limited query capabilities vs SQL — No JOINs (denormalization needed) — Reads can be costly if not carefully structured — 1 write/sec per document limit (fine for hackathon scale) |

---

### ADR-003 — Google ADK as agent framework

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-003 |
| **Date** | 2026-08-19 |
| **Question** | Which framework to use for the AI agent? |
| **Options** | 1. Google ADK (Agent Development Kit) 2. LangChain 3. Custom agent loop 4. CrewAI |
| **Decision** | Google ADK |
| **Reason** | - Hackathon requirement: must use Google Cloud AI tools — Native Gemini integration — Structured tool calling support — Designed for production agents (not just demos) — Aligns with hackathon judging criteria (Google Cloud usage) |
| **Consequences** | - Newer framework, smaller community — Locked into Google AI ecosystem — May have fewer examples/docs compared to LangChain |

---

### ADR-004 — Pub/Sub for asynchronous processing

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-004 |
| **Date** | 2026-08-19 |
| **Question** | How to handle async processing of GitHub webhooks and opportunity collection? |
| **Options** | 1. Process synchronously in webhook handler 2. Cloud Pub/Sub 3. Cloud Tasks 4. Background threads |
| **Decision** | Cloud Pub/Sub |
| **Reason** | - Decouples webhook acknowledgment from processing (critical for GitHub's 10s timeout) — Built-in retry with exponential backoff — Dead letter queue support for failed messages — Native Google Cloud service (hackathon points) — Push subscriptions work directly with Cloud Run — At-least-once delivery with our idempotency layer ensures exactly-once processing |
| **Consequences** | - At-least-once delivery requires idempotency handling — Additional infrastructure to configure — Slight complexity in local development (need Pub/Sub emulator or direct connection) |

---

### ADR-005 — Explicit decision policy (not prompt-based)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-005 |
| **Date** | 2026-08-19 |
| **Question** | How should the system decide whether to notify the user about an observation? |
| **Options** | 1. Include notification logic in the agent prompt ("decide if this is important enough to notify") 2. Explicit Python decision policy function 3. Rule engine (e.g., Drools) |
| **Decision** | Explicit Python decision policy |
| **Reason** | — **Transparency:** Can show exact rules on dashboard ("why did the agent decide this?") — **Determinism:** Same input always produces same decision — **Testability:** Unit-testable without AI — **Demo value:** Judges can see explicit logic, not a black box — **Separation of concerns:** AI judges importance (significance score), code makes the binary decision — The plan specifically requires this: "Decision policy should remain explicit (if/else, not 'agent decided inside one big prompt')" |
| **Consequences** | - Policy rules must be maintained separately from prompts — Significance score from Gemini is the bridge between AI judgment and deterministic decision — Need to keep prompt and policy in sync (both need to agree on what "significance" means) |

---

### ADR-006 — API versioning with `/api/v1/`

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-006 |
| **Date** | 2026-08-19 |
| **Question** | Should we version the API? |
| **Options** | 1. No versioning (YAGNI for hackathon) 2. URL-based versioning (`/api/v1/`) 3. Header-based versioning |
| **Decision** | URL-based versioning (`/api/v1/`) |
| **Reason** | - Low cost to implement (just path prefix) — Prevents breaking frontend when backend changes — Professional practice, good for judges — Easy to test (visible in URL) |
| **Consequences** | - Slightly longer URLs — Need to maintain version prefix in all routes |

---

### ADR-007 — GitHub OAuth App (not PAT)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-007 |
| **Date** | 2026-08-19 |
| **Question** | How should users connect their GitHub accounts? |
| **Options** | 1. Personal Access Token (user pastes token) 2. GitHub OAuth App 3. GitHub App (installation) |
| **Decision** | GitHub OAuth App |
| **Reason** | - More polished user experience for demo — Standard OAuth flow that judges expect — User doesn't need to navigate GitHub settings — Access scoped to what the OAuth App requests — Better security story (token managed by backend, not pasted by user) |
| **Consequences** | - More setup required (OAuth App registration, callback URL, state parameter) — Need to handle token storage in Secret Manager — Need to implement full OAuth callback flow |

---

### ADR-008 — Weighted average for skill score updates

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-008 |
| **Date** | 2026-08-19 |
| **Question** | How should skill scores (0-10) be updated when new observations arrive? |
| **Options** | 1. Absolute overwrite (Gemini sets score directly) 2. Delta-based (+/- adjustments) 3. Weighted average (new = old × 0.7 + assessment × 0.3) |
| **Decision** | Weighted average: `new_score = old_score × 0.7 + assessment × 0.3` |
| **Reason** | - Stable: prevents wild score swings from single observations — Explainable: "your score gradually trends toward your real ability" — Resilient: one bad Gemini assessment doesn't nuke the score — Believable demo results |
| **Consequences** | - Scores change slowly (may need multiple observations to see significant movement) — Weight parameter (0.3) may need tuning — New skills start at Gemini's first assessment (no averaging with 0) |

---

### ADR-009 — Telegram webhook mode (not polling)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-009 |
| **Date** | 2026-08-19 |
| **Question** | How should the Telegram bot receive messages? |
| **Options** | 1. Long polling (getUpdates) 2. Webhook mode |
| **Decision** | Webhook mode |
| **Reason** | - Production-ready architecture — Lower latency than polling — Works naturally with Cloud Run (HTTP endpoint) — No need for long-running polling process — More resource-efficient |
| **Consequences** | - Need HTTPS endpoint (Cloud Run provides this) — Need to register webhook URL with Telegram — Need to handle webhook validation |

---

### ADR-010 — Gemini-assigned significance score with intensity-based thresholds

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-010 |
| **Date** | 2026-08-19 |
| **Question** | How to determine if an observation is "significant" enough to notify? |
| **Options** | 1. Fixed rules (any skill change >= 1 point) 2. Gemini assigns significance score, threshold per intensity 3. User-defined rules |
| **Decision** | Gemini assigns a significance score (1-10), threshold is configurable per intensity level (chill=7, normal=5, brutal=3) |
| **Reason** | - Leverages AI judgment for nuanced significance assessment — Intensity settings provide user control — Threshold logic stays in deterministic decision policy — Escalation rules can override threshold for critical events |
| **Consequences** | - Significance score quality depends on Gemini prompt quality — Need to calibrate: what does "significance 7" mean vs "significance 3"? — Prompt must clearly define the significance scale |

---

### ADR-011 — Multiple GitHub repos supported

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-011 |
| **Date** | 2026-08-19 |
| **Question** | Can a user connect multiple GitHub repos? |
| **Options** | 1. Single repo only 2. Multiple repos |
| **Decision** | Multiple repos |
| **Reason** | - Users typically work across multiple repos — More data for skill analysis — Better demo story |
| **Consequences** | - Need to register webhook on each repo — Need to look up user by repo when webhook fires — `connectedRepos` stored as array in user document — Need webhook cleanup when repos are disconnected |

---

### ADR-012 — Auto-detect language from user message

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-012 |
| **Date** | 2026-08-19 |
| **Question** | What language should the agent communicate in? |
| **Options** | 1. English only 2. User-selected language 3. Auto-detect from user message |
| **Decision** | Auto-detect from user message, respond in the same language |
| **Reason** | - Better UX — no need to configure — Gemini natively handles language detection — Natural for bilingual users who may switch between languages — Still store preferred language in profile as hint for proactive notifications |
| **Consequences** | - Proactive notifications (no user message to detect from) use the stored `language` preference — Gemini prompt must include instruction to respond in user's language — Quality may vary between languages |

---

### ADR-013 — Firebase Auth with Google + GitHub + Email/Password

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-013 |
| **Date** | 2026-08-19 |
| **Question** | Which sign-in methods to support? |
| **Options** | 1. Google only 2. Google + GitHub 3. Google + Email/Password 4. Google + GitHub + Email/Password |
| **Decision** | Google + GitHub + Email/Password |
| **Reason** | - Google: fastest sign-in for most users — GitHub: natural for developer audience, links to their coding identity — Email/Password: fallback for users who don't want OAuth — All three are trivial to enable in Firebase Auth console |
| **Consequences** | - Need to handle account linking (same email, different providers) — Firebase handles most complexity — Frontend needs three sign-in buttons |

---

## Open Questions

These decisions have NOT been made yet. They require further discussion or information.

### OQ-001 — Opportunity Sources

| Field | Value |
|-------|-------|
| **Question** | Which RSS/API sources should the opportunity collector use? |
| **Status** | **WAITING FOR USER INPUT** |
| **Impact** | Blocks implementation of F9 (Opportunity Discovery) |
| **Options** | Hacker News, Dev.to, GitHub Trending, Reddit, Stack Overflow, custom list |
| **Note** | User said "I will provide it later" |

### OQ-002 — Frontend Styling Framework

| Field | Value |
|-------|-------|
| **Question** | Which CSS framework / component library should the frontend use? |
| **Status** | Open |
| **Impact** | Frontend implementation |
| **Options** | CSS Modules, Tailwind CSS, Chakra UI, shadcn/ui |
| **Note** | To be decided by frontend developer (Vlad) |

### OQ-003 — Charting Library

| Field | Value |
|-------|-------|
| **Question** | Which library for skill visualization (radar chart, bar charts)? |
| **Status** | Open |
| **Impact** | Dashboard implementation |
| **Options** | Recharts, Chart.js, D3.js, Nivo |
| **Note** | To be decided by frontend developer (Vlad) |

### OQ-004 — Local Development Experience

| Field | Value |
|-------|-------|
| **Question** | How to handle Pub/Sub, Firestore, and webhooks in local development? |
| **Status** | Open |
| **Impact** | Developer experience |
| **Options** | Firebase emulator suite, direct cloud connections, ngrok for webhooks |
| **Note** | Need to decide before implementation starts |
