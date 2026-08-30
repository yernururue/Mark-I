# Mark-I — Technical Requirements Document

> **Status:** Draft v1.2
> **Last updated:** 2026-08-29  
> **Authors:** Yernur (backend/agent), Vlad (frontend)

---

## 1. System Overview

Mark-I is a cloud-native workspace for **Multiple Customizable Agents**. A user can create several specialized agents, switch between isolated conversations, customize each agent's identity and behavior, and run work with scoped context and traceable ownership. Developer mentoring is the first agent template and GitHub remains the first deep activity integration.

The product, frontend, backend, persistence layer, and runtime all use **agent** as the single domain term, with stable identifiers such as `agentId`.

The platform consists of:

- **Frontend** — Next.js web app on a Next-compatible Firebase/Google runtime
- **Backend** — FastAPI service running on Cloud Run
- **Agent Runtime** — Google ADK + Gemini instances created from stored agent configurations
- **Run Orchestrator** — routes assignments, schedules concurrent runs, enforces limits, and records state
- **Integrations** — GitHub (OAuth + webhooks), Telegram Bot API
- **Infrastructure** — Firestore, Pub/Sub, Cloud Scheduler, Secret Manager

---

## 2. Architecture Summary

This is the directional target architecture. The existing frontend dashboard is visually frozen: its shell, roster, chat canvas, layout, styles, navigation, and component arrangement remain in place. Changes occur behind that interface in services, state, validation, and backend adapters.

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  Next.js + Firebase Auth + Next-compatible hosting           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Dashboard │ │ Agents   │ │  Chat    │ │Onboarding│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│         │            │            │            │             │
│         └────────────┴────────────┴────────────┘             │
│                          │                                   │
│              Firebase Auth (ID Token)                        │
│                          │                                   │
│              Firestore Listeners (realtime)                  │
└─────────────┬────────────┴───────────────────────────────────┘
              │ REST API (Bearer token)
              ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│  FastAPI on Cloud Run                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ API      │ │ Webhooks │ │ Run Orch.│ │ Decision │       │
│  │ Routes   │ │ Handler  │ │ + Router │ │ Policy   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│         │            │            │            │             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ GitHub   │ │ Telegram │ │ Opportu- │                    │
│  │ Service  │ │ Service  │ │ nity Svc │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
│         │            │            │                          │
│  ┌────────────────────────────────────────┐                  │
│  │        Agent Runtime (ADK + Gemini)    │                  │
│  │  Loads: identity, role, instructions,  │                  │
│  │  tool grants, private/shared context   │                  │
│  │  Emits: messages, artifacts, handoffs, │                  │
│  │  observations, decisions, run events   │                  │
│  └────────────────────────────────────────┘                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────────────┐
        ▼              ▼                      ▼
  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐
  │Firestore │  │  Pub/Sub     │  │ Secret Manager    │
  │          │  │              │  │ (GitHub tokens)   │
  └──────────┘  └──────────────┘  └───────────────────┘
                       │
                ┌──────┴──────┐
                ▼             ▼
         ┌──────────┐  ┌──────────────┐
         │ Cloud    │  │ Cloud        │
         │ Scheduler│  │ Run (worker) │
         └──────────┘  └──────────────┘
```

---

## 3. Frontend Architecture

### 3.1 Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | Next.js 16 (App Router) |
| UI runtime | React 19 |
| Language | TypeScript (strict) |
| Auth | Firebase Auth (client SDK) |
| Realtime | Firestore client SDK (onSnapshot) |
| HTTP | Typed wrapper around Fetch API |
| Styling | Global CSS with Tailwind 4 build processing |
| Icons | Lucide React |
| Development data | Explicit localStorage adapter and simulators |
| Hosting | Next-compatible runtime; final Firebase deployment mode must be confirmed |

### 3.2 Pages & Routes

| Route | Purpose | Auth Required |
|-------|---------|---------------|
| `/` | Landing / redirect to dashboard | No |
| `/login` | Sign-in page | No |
| `/onboarding` | Workspace defaults and first-agent setup | Yes |
| `/dashboard` | Existing chat-first workspace and agent switcher | Yes |
| `/agents` | Create and manage agents | Yes |
| `/agents/[agentId]` | Agent configuration and lifecycle | Yes |
| `/runs/[runId]` | Live run timeline, outputs, controls, and blockers | Yes |
| `/chat` | Compatibility redirect to `/dashboard` | Yes |
| `/settings` | Workspace defaults, integrations, and preferences | Yes |
| `/auth/github/callback` | GitHub OAuth callback handler | Yes |

The existing `/agents` routes already match the product terminology and should remain canonical. Selected agent and conversation identity must be deep-linkable; changing agents must load a separate conversation rather than mutate recipients on the current thread.

### 3.3 Frontend ↔ Backend Communication

**REST API calls:**
- All API requests include `Authorization: Bearer <firebase-id-token>` header
- Frontend obtains token via `firebase.auth().currentUser.getIdToken()`
- Token refreshed automatically by Firebase SDK
- All endpoints prefixed with `/api/v1/`
- Remote mode must expose real list/create/select conversation contracts; the frontend must not fabricate a single workspace conversation.
- External JSON must be decoded at the DTO boundary before it becomes agent domain state.

**Firestore Realtime:**
- Frontend reads directly from Firestore for realtime updates:
  - `users/{uid}` — profile, skills
  - `users/{uid}/agents/{agentId}` — agent identity, behavior, and grants
  - `users/{uid}/runs/{runId}` — assignment and run lifecycle
  - `users/{uid}/artifacts/{artifactId}` — outputs shared by reference
  - `users/{uid}/handoffs/{handoffId}` — traceable agent-to-agent handoffs
  - `users/{uid}/observations/{obsId}` — observation feed
  - `users/{uid}/messages/{msgId}` — chat messages
  - `users/{uid}/decisions/{decisionId}` — decision log
- Frontend does NOT write to Firestore directly (all mutations go through backend API)
- Firestore Security Rules enforce read-only access for authenticated users to their own data

**Frontend data boundaries:**
- Firestore/API payloads use typed agent DTOs and stable `agentId` values.
- Mappers validate transport payloads and produce agent summaries/details for UI use.
- Profile, roster, agent detail, conversations, messages, runs, and integrations have focused loading/error/subscription state.
- The local adapter implements the same repository contracts as the remote adapter and is selected explicitly.
- Production configuration fails fast instead of silently falling back to local preview data.

### 3.4 Frontend Responsibilities

The frontend is responsible for:
- UI rendering and interaction
- Firebase Auth client-side flow
- GitHub OAuth redirect initiation
- Firestore listener management for realtime updates
- Agent creation/configuration and multi-run status presentation
- Canonical selected-agent and selected-conversation state
- One-to-one conversation isolation when switching agents
- REST API calls for mutations and actions
- Client-side routing and navigation

The frontend is NOT responsible for:
- Business logic
- Agent execution and run orchestration
- Webhook handling
- Decision making
- Direct Firestore writes
- Secret management

### 3.5 Existing dashboard preservation

- Preserve the current dashboard shell, roster rail, chat canvas, composer, layout, styles, navigation, and component arrangement exactly.
- Do not add panels, widgets, badges, unread/activity indicators, analytics surfaces, or new dashboard navigation.
- Connect existing controls and states to validated backend services without changing their visual output.
- Remove unused subscriptions, assets, selectors, and dependencies only after proving they do not support the current dashboard.
- One-to-one agent threads are isolated in the data layer while using the existing chat interface; group-chat UI is out of scope.

### 3.6 Agent customization contract

The frontend agent model supports the fields already represented by the approved UI:

- stable `agentId` and lifecycle state;
- name, role, template, objective, and instructions;
- tone, tool grants, and context grants;
- active/paused/archived lifecycle and schema version;
- timestamps required by current list/detail views.

Create and update commands are separate types. Template and capability metadata come from one shared catalog used by onboarding and management.

---

## 4. Backend Architecture

### 4.1 Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Language | Python 3.11+ |
| Runtime | Cloud Run (managed) |
| Auth verification | Firebase Admin SDK |
| Database | Firestore (via firebase-admin) |
| AI Framework | Google ADK (Agent Development Kit) |
| LLM | Gemini (via Vertex AI) |
| Message queue | Cloud Pub/Sub |
| Scheduler | Cloud Scheduler |
| Secrets | Google Secret Manager |
| Telegram | python-telegram-bot / HTTP API |
| GitHub | PyGithub / HTTP API |

### 4.2 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Environment & config
│   ├── dependencies.py            # Dependency injection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # API v1 router aggregator
│   │   │   ├── auth.py            # Auth endpoints
│   │   │   ├── users.py           # User profile endpoints
│   │   │   ├── dashboard.py       # Dashboard data endpoint
│   │   │   ├── skills.py          # Skills endpoints
│   │   │   ├── observations.py    # Observations endpoints
│   │   │   ├── chat.py            # Chat endpoints
│   │   │   ├── agents.py         # agent CRUD and configuration
│   │   │   ├── runs.py            # Start, inspect, pause, cancel runs
│   │   │   ├── artifacts.py       # Run output metadata
│   │   │   ├── github.py          # GitHub integration endpoints
│   │   │   └── telegram.py        # Telegram linking endpoints
│   │   │
│   │   └── webhooks/
│   │       ├── __init__.py
│   │       ├── github.py          # GitHub webhook receiver
│   │       └── telegram.py        # Telegram webhook receiver
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py        # User CRUD
│   │   ├── github_service.py      # GitHub API interactions
│   │   ├── telegram_service.py    # Telegram Bot API
│   │   ├── observation_service.py # Observation CRUD
│   │   ├── skill_service.py       # Skill tracking logic
│   │   ├── chat_service.py        # Unified chat handling
│   │   ├── agent_service.py      # agent lifecycle and validation
│   │   ├── run_service.py         # Run state and concurrency limits
│   │   ├── routing_service.py     # Route events/assignments to agents
│   │   ├── handoff_service.py     # Explicit cross-agent handoffs
│   │   ├── opportunity_service.py # Opportunity collection
│   │   └── decision_service.py    # Decision policy engine
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                # User Pydantic models
│   │   ├── observation.py         # Observation models
│   │   ├── skill.py               # Skill models
│   │   ├── message.py             # Chat message models
│   │   ├── agent.py              # agent configuration and grants
│   │   ├── run.py                 # Assignment and run lifecycle
│   │   ├── artifact.py            # Run outputs and shared references
│   │   ├── handoff.py             # Collaboration records
│   │   ├── decision.py            # Decision models
│   │   └── github.py              # GitHub event models
│   │
│   └── middleware/
│       ├── __init__.py
│       └── auth.py                # Firebase token verification
│
├── ai/
│   ├── __init__.py
│   ├── runtime.py                 # Build an ADK runtime from agent config
│   ├── orchestrator.py            # Dispatch and coordinate concurrent runs
│   ├── router.py                  # Select agents for messages/events
│   ├── templates.py               # Mentor, Designer, and starter templates
│   ├── prompts.py                 # Composable role and behavior prompts
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── profile_tools.py       # read_user_profile
│   │   ├── skill_tools.py         # read_skills, update_skill_score
│   │   ├── observation_tools.py   # read_observations, create_observation, search_observations
│   │   ├── telegram_tools.py      # send_telegram_message
│   │   ├── opportunity_tools.py   # search_opportunities
│   │   ├── github_tools.py        # query_github_repos
│   │   └── decision_tools.py      # explain_decision_policy
│   │
│   └── analyzers/
│       ├── __init__.py
│       ├── github_analyzer.py     # GitHub event → structured analysis
│       └── opportunity_analyzer.py # Opportunity → relevance analysis
│
├── telegrambot/
│   ├── __init__.py
│   ├── bot.py                     # Bot setup and command handlers
│   ├── handlers.py                # /start, /link command handlers
│   └── webhook.py                 # Webhook setup
│
├── workers/
│   ├── __init__.py
│   ├── github_worker.py           # Pub/Sub → GitHub event processor
│   ├── opportunity_worker.py      # Pub/Sub → Opportunity collector
│   └── agent_run_worker.py       # Pub/Sub → isolated agent run
│
├── requirements.txt
├── Dockerfile
└── cloudbuild.yaml
```

### 4.3 Authentication Flow

```
Frontend                    Backend
   │                           │
   │  1. Firebase Auth login   │
   │  (client-side)            │
   │                           │
   │  2. Get ID token          │
   │  getIdToken()             │
   │                           │
   │  3. API request           │
   │  Authorization: Bearer    │
   │  <id_token>               │
   │ ─────────────────────────>│
   │                           │  4. Verify token
   │                           │  firebase_admin.auth
   │                           │  .verify_id_token()
   │                           │
   │                           │  5. Extract uid
   │                           │  from decoded token
   │                           │
   │  6. Response              │
   │ <─────────────────────────│
```

### 4.4 Backend Responsibilities

The backend is responsible for:
- Firebase token verification on all API requests
- All Firestore read/write operations
- GitHub OAuth token exchange and storage
- GitHub webhook processing and event analysis
- Telegram bot command handling and message sending
- agent configuration, runtime construction, and concurrent run orchestration
- Per-user concurrency limits, cancellation, retries, and run isolation
- Permission-aware context retrieval and tool grants
- Traceable artifacts and agent-to-agent handoffs
- Decision policy execution
- Opportunity collection and analysis
- Pub/Sub message publishing and consuming
- Secret management (via Secret Manager)

The backend is NOT responsible for:
- Client-side UI rendering
- Firebase Auth sign-in flow (client-side)
- Frontend state management
- CSS/styling decisions

---

## 5. AI Architecture

### 5.1 Architecture Layers

The AI system is split into clearly separated layers:

```
┌─────────────────────────────────────────────────┐
│                  TRIGGER LAYER                   │
│  GitHub webhook, Telegram message, Chat request, │
│  Cloud Scheduler cron                            │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│             ROUTING + ORCHESTRATION LAYER        │
│  Resolve target agent(s), create run records,   │
│  enforce grants/concurrency, dispatch workers    │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              CONTEXT RETRIEVAL LAYER             │
│  Load agent config and permitted private/shared │
│  context; never inject unrestricted user context │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                 AI REASONING LAYER               │
│  agent runtime instance (ADK + Gemini)          │
│  - Analyzes input with authorized context        │
│  - Produces structured output                    │
│  - Calls only tools granted to this agent       │
│  - Can propose an explicit handoff               │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              STRUCTURED OUTPUT LAYER             │
│  Pydantic models enforce output schema:          │
│  - GitHubAnalysis                                │
│  - OpportunityRelevance                          │
│  - ChatResponse                                  │
│  - ObservationData                               │
│  - RunUpdate / Artifact / HandoffRequest         │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│             DECISION POLICY LAYER                │
│  DETERMINISTIC Python code (NOT in prompt):      │
│  - Evaluate significance score                   │
│  - Apply intensity threshold                     │
│  - Check escalation rules                        │
│  - Decide: notify / log silently                 │
│  - Record decision with reason                   │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                  ACTION LAYER                    │
│  - Write observation to Firestore                │
│  - Update skill scores                           │
│  - Send Telegram notification                    │
│  - Store decision record                         │
│  - Update run status and persist artifacts       │
│  - Publish approved handoffs as new assignments  │
│  - Return chat response                          │
└─────────────────────────────────────────────────┘
```

### 5.2 Agent Runtime Design (ADK)

**Runtime identity:** `agent:{agentId}`; every execution also carries a unique `runId`.

**Model:** `gemini-2.0-flash` (or `gemini-1.5-pro` for complex analysis)

**Agent configuration:** Stored data, not a hard-coded singleton. It includes:
- Display identity: name and role
- Objective and user-authored instructions
- Template type (`mentor`, `designer`, or `custom`)
- Tone and notification policy
- Granted tools and integrations
- Private context scope and allowed shared workspace sources
- Lifecycle state (`active`, `paused`, `archived`)

**Prompt assembly:** The runtime composes the system prompt from platform safety rules, agent configuration, assignment, and authorized context. Template prompts provide editable defaults; they do not create separate code paths.

**Execution model:** The orchestrator creates one durable run record per assignment, dispatches independent runs through Pub/Sub workers, and allows multiple agents to execute concurrently. Run transitions are `queued → running → waiting-for-user | completed | failed | cancelled`. One failed run cannot terminate unrelated work.

**Tools:**

| Tool | Purpose | Category |
|------|---------|----------|
| `read_user_profile` | Get user's goal, intensity, settings | Read |
| `read_skills` | Get current skill scores | Read |
| `read_observations` | Get recent observations | Read |
| `search_observations` | Search observations by concept/source | Read |
| `send_telegram_message` | Send message to user's Telegram | Action |
| `update_skill_score` | Update a skill score (weighted avg) | Write |
| `create_observation` | Create a new observation | Write |
| `search_opportunities` | Query opportunity sources | Read |
| `query_github_repos` | Get info about connected repos | Read |
| `explain_decision_policy` | Explain why a decision was made | Read |
| `read_shared_artifact` | Read an explicitly shared workspace artifact | Read |
| `publish_artifact` | Persist an output and attach it to the run | Write |
| `request_handoff` | Propose work for another agent with a traceable payload | Action |
| `update_run_status` | Publish progress or a blocker to the run timeline | Write |

### 5.3 Critical Boundary: Agent vs. Business Logic

| Concern | Handled By | Rationale |
|---------|-----------|-----------|
| "What concepts are in this code?" | Agent (Gemini) | Requires understanding |
| "How proficient is this code?" | Agent (Gemini) | Requires judgment |
| "Should we notify the user?" | Decision Policy (Python) | Must be deterministic and explainable |
| "How to update skill scores?" | Skill Service (Python) | Math formula, not AI |
| "Is this opportunity relevant?" | Agent (Gemini) | Requires semantic matching |
| "What intensity threshold to use?" | Decision Policy (Python) | Configuration, not AI |
| "What tone to use in messages?" | Agent (Gemini) | Persona-aware natural language |
| "Which agent is explicitly addressed?" | Router (Python) | Deterministic identity selection |
| "May this agent use a tool or read context?" | Authorization policy (Python) | Must be enforceable and auditable |
| "Can another run start now?" | Orchestrator (Python) | Concurrency and budget enforcement |
| "What work should a specialist perform?" | Agent (Gemini) | Role-specific reasoning within assignment |
| "Should a handoff execute?" | Handoff policy + user grants | Prevents uncontrolled delegation |

### 5.4 Skill Update Formula

```python
def update_skill(current_score: float, assessment: float, weight: float = 0.3) -> float:
    """
    Weighted average skill update.
    
    current_score: existing score (0-10), or 0 if new skill
    assessment: Gemini's proficiency assessment for this observation (0-10)
    weight: how much the new assessment influences the score (default 0.3)
    
    Returns: new score clamped to [0, 10]
    """
    if current_score == 0:  # New skill
        return min(assessment, 10.0)
    
    new_score = current_score * (1 - weight) + assessment * weight
    return max(0.0, min(10.0, round(new_score, 1)))
```

### 5.5 Decision Policy

```python
INTENSITY_THRESHOLDS = {
    "chill": 7,    # Only notify for highly significant events
    "normal": 5,   # Balanced notifications  
    "brutal": 3,   # Notify for almost everything
}

ESCALATION_RULES = [
    "repeated_error",      # Same concept, negative sentiment, 3+ times
    "skill_regression",    # Skill score decreased by >= 1 point
    "new_concept",         # First time a concept appears
    "milestone_reached",   # Skill score crosses 5 or 8
]

def should_notify(
    significance: int,
    intensity: str,
    escalation_flags: list[str],
) -> tuple[bool, str]:
    """
    Returns (should_notify, reason).
    """
    threshold = INTENSITY_THRESHOLDS[intensity]
    
    # Escalation overrides threshold
    if any(flag in ESCALATION_RULES for flag in escalation_flags):
        return True, f"Escalation: {', '.join(escalation_flags)}"
    
    if significance >= threshold:
        return True, f"Significance {significance} >= threshold {threshold}"
    
    return False, f"Significance {significance} < threshold {threshold}"
```

---

## 6. Integration Architecture

### 6.1 GitHub Integration

**Auth Flow:**
```
Frontend                  Backend                    GitHub
   │                         │                         │
   │ 1. Click "Connect       │                         │
   │    GitHub"               │                         │
   │                         │                         │
   │ 2. GET /api/v1/github/  │                         │
   │    auth-url              │                         │
   │ <───────────────────────│                         │
   │                         │                         │
   │ 3. Redirect to GitHub   │                         │
   │ ────────────────────────────────────────────────> │
   │                         │                         │
   │ 4. User authorizes      │                         │
   │ <────────────────────────────────────────────────│
   │                         │                         │
   │ 5. Redirect to callback │                         │
   │    with ?code=xxx       │                         │
   │                         │                         │
   │ 6. POST /api/v1/github/ │                         │
   │    callback?code=xxx    │                         │
   │ ───────────────────────>│                         │
   │                         │ 7. Exchange code         │
   │                         │    for token             │
   │                         │ ───────────────────────>│
   │                         │ <───────────────────────│
   │                         │                         │
   │                         │ 8. Store token in        │
   │                         │    Secret Manager        │
   │                         │                         │
   │                         │ 9. Fetch user repos      │
   │                         │ ───────────────────────>│
   │                         │ <───────────────────────│
   │                         │                         │
   │ 10. Return repo list    │                         │
   │ <───────────────────────│                         │
   │                         │                         │
   │ 11. User selects repos  │                         │
   │ POST /api/v1/github/    │                         │
   │      repos              │                         │
   │ ───────────────────────>│                         │
   │                         │ 12. Register webhooks   │
   │                         │ ───────────────────────>│
   │                         │ <───────────────────────│
   │ 13. Confirmation        │                         │
   │ <───────────────────────│                         │
```

**Webhook Processing:**
```
GitHub                   Backend                   Pub/Sub          Worker
  │                         │                         │               │
  │ 1. Event (push/PR/etc)  │                         │               │
  │ ───────────────────────>│                         │               │
  │                         │                         │               │
  │                         │ 2. Validate signature   │               │
  │                         │    (HMAC SHA-256)        │               │
  │                         │                         │               │
  │                         │ 3. Publish event        │               │
  │                         │ ───────────────────────>│               │
  │                         │                         │               │
  │  4. 200 OK (fast)       │                         │               │
  │ <───────────────────────│                         │               │
  │                         │                         │ 4. Deliver    │
  │                         │                         │ ─────────────>│
  │                         │                         │               │
  │                         │                         │  5. Process:  │
  │                         │                         │  - Load user  │
  │                         │                         │  - Gemini     │
  │                         │                         │    analyze    │
  │                         │                         │  - Create     │
  │                         │                         │    observation│
  │                         │                         │  - Update     │
  │                         │                         │    skills     │
  │                         │                         │  - Decision   │
  │                         │                         │    policy     │
  │                         │                         │  - Notify if  │
  │                         │                         │    needed     │
  │                         │                         │  6. ACK       │
  │                         │                         │ <─────────────│
```

### 6.2 Telegram Integration

**Webhook Mode:** Telegram bot uses webhook mode (not polling). Webhook URL registered with Telegram Bot API.

**Link Flow:**
```
Web Frontend              Backend                    Telegram Bot
     │                       │                           │
     │ 1. POST /api/v1/      │                           │
     │    telegram/link       │                           │
     │ ──────────────────────>│                           │
     │                       │ 2. Generate 6-char code   │
     │                       │    (TTL: 10 min)          │
     │                       │    Store in Firestore     │
     │ 3. Return code        │                           │
     │ <──────────────────────│                           │
     │                       │                           │
     │ 4. User sends          │                           │
     │    /link CODE          │                           │
     │    to bot              │                           │
     │                       │                           │
     │                       │ 5. /webhook/telegram      │
     │                       │ <─────────────────────────│
     │                       │                           │
     │                       │ 6. Validate code          │
     │                       │    Link telegram_id ↔ uid │
     │                       │    Delete code            │
     │                       │                           │
     │                       │ 7. Send confirmation      │
     │                       │ ──────────────────────────>│
```

### 6.3 Pub/Sub Topics

| Topic | Publisher | Subscriber | Purpose |
|-------|----------|------------|---------|
| `github-events` | GitHub webhook handler | GitHub worker | Async processing of GitHub events |
| `opportunity-collect` | Cloud Scheduler | Opportunity worker | Trigger opportunity collection |

### 6.4 Cloud Scheduler Jobs

| Job | Schedule | Target | Purpose |
|-----|----------|--------|---------|
| `opportunity-trigger` | Every hour (demo) / Every 24h (prod) | Pub/Sub `opportunity-collect` | Trigger opportunity discovery |

---

## 7. Security

### 7.1 Authentication

- All frontend API calls include Firebase ID token
- Backend verifies token on every request via `firebase_admin.auth.verify_id_token()`
- Token expiration handled by Firebase SDK (auto-refresh)

### 7.2 Secret Management

| Secret | Storage | Access |
|--------|---------|--------|
| GitHub OAuth client secret | Secret Manager | Backend only |
| GitHub user access tokens | Secret Manager | Backend only, per-user |
| Telegram bot token | Secret Manager | Backend only |
| Firebase service account | Cloud Run env / Secret Manager | Backend only |
| GitHub webhook secret | Secret Manager | Backend only |

**NEVER store in Firestore:**
- OAuth tokens
- API keys
- Webhook secrets
- Service account credentials

### 7.3 Webhook Security

- **GitHub webhooks:** Validated via HMAC SHA-256 signature (`X-Hub-Signature-256`)
- **Telegram webhooks:** Validated via secret token in webhook URL path

### 7.4 Firestore Security Rules

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
      
      match /decisions/{decId} {
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
  }
}
```

---

## 8. Deployment

### 8.1 Frontend

- **Current build:** `npm run build` (`next build`)
- **Runtime requirement:** the current app has dynamic routes and server-rendered request parameters; it is not documented as a static export.
- **Hosting decision:** use a Firebase/Google deployment option that supports the Next.js runtime, or explicitly change the route/runtime architecture for static export before deployment.
- **Validation:** build once with explicit local-preview configuration and once with explicit remote configuration.
- **Security:** frontend environment files contain browser-safe `NEXT_PUBLIC_*` values only.

Browser-safe frontend variables:

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase web client API key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase Auth domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase messaging sender ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase web app ID |
| `NEXT_PUBLIC_API_URL` | Backend `/api/v1` base URL |
| `NEXT_PUBLIC_DATA_MODE` | Explicit `local` or remote/Firebase adapter selection |
| `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` | Public Telegram bot username |

### 8.2 Backend

- **Build:** Docker container
- **Host:** Cloud Run (fully managed)
- **Deploy:** `gcloud run deploy` or Cloud Build
- **URL:** `https://<service>-<hash>.run.app`
- **Config:**
  - Min instances: 0 (hackathon budget)
  - Max instances: 5
  - Memory: 512MB
  - CPU: 1
  - Timeout: 300s (for AI processing)
  - Concurrency: 80

### 8.3 Environment Variables (Backend)

| Variable | Source | Description |
|----------|--------|-------------|
| `GCP_PROJECT_ID` | Cloud Run env | GCP project ID |
| `FIRESTORE_DATABASE` | Cloud Run env | Firestore database ID (default) |
| `GITHUB_CLIENT_ID` | Cloud Run env | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET_NAME` | Secret Manager ref | Secret Manager secret name for OAuth secret |
| `GITHUB_WEBHOOK_SECRET_NAME` | Secret Manager ref | Secret Manager secret name for webhook secret |
| `TELEGRAM_BOT_TOKEN_NAME` | Secret Manager ref | Secret Manager secret name for bot token |
| `GEMINI_MODEL` | Cloud Run env | Gemini model name |
| `PUBSUB_GITHUB_TOPIC` | Cloud Run env | Pub/Sub topic for GitHub events |
| `PUBSUB_OPPORTUNITY_TOPIC` | Cloud Run env | Pub/Sub topic for opportunity collection |
| `FRONTEND_URL` | Cloud Run env | Frontend URL for OAuth callback |

---

## 9. Technology Decision Summary

See [DECISIONS.md](DECISIONS.md) for detailed ADRs.

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | Next.js 16 App Router | React ecosystem, dynamic route support, Firebase integration |
| Product/technical naming | Agent everywhere | One consistent domain term across UI, API, storage, and runtime |
| Dashboard direction | Freeze the existing chat-first UI | Refactor services/state and connect the backend without visual or layout changes |
| Backend framework | FastAPI | Async Python, auto-docs, type safety |
| Database | Firestore | Firebase ecosystem, realtime, serverless |
| Auth | Firebase Auth | Multi-provider, client SDK, token verification |
| AI framework | Google ADK | Google Cloud requirement, tool orchestration |
| LLM | Gemini | Hackathon requirement (Google Cloud) |
| Message queue | Cloud Pub/Sub | Google Cloud native, decouples webhook from processing |
| Scheduler | Cloud Scheduler | Google Cloud native, cron-like |
| Secret storage | Secret Manager | Google Cloud native, not in Firestore |
| Hosting (frontend) | Firebase Hosting | CDN, easy deploy, same Firebase project |
| Hosting (backend) | Cloud Run | Containerized, auto-scaling, Google Cloud |
| GitHub auth | OAuth App | Full OAuth flow, more polished for demo |
| Telegram mode | Webhook (not polling) | Production-ready, lower latency |
