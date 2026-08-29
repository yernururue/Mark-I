# Mark-I — Architecture Document

> **Status:** Draft v1.1  
> **Last updated:** 2026-08-29

---

## 1. System Architecture

```mermaid
graph TB
    subgraph "User Interfaces"
        WEB["Web App<br/>(Next.js)"]
        TG["Telegram Bot"]
    end

    subgraph "Firebase"
        AUTH["Firebase Auth"]
        HOSTING["Firebase Hosting"]
        FS["Cloud Firestore"]
    end

    subgraph "Backend (Cloud Run)"
        API["FastAPI<br/>API Routes"]
        WH["Webhook<br/>Handlers"]
        CHAT_SVC["Chat<br/>Service"]
        ROUTER["Agent<br/>Router"]
        ORCH["Run<br/>Orchestrator"]
        DECISION["Decision<br/>Policy Engine"]
        GH_SVC["GitHub<br/>Service"]
        TG_SVC["Telegram<br/>Service"]
        OPP_SVC["Opportunity<br/>Service"]
    end

    subgraph "AI Layer"
        RUNTIME["Configurable<br/>Agent Runtime"]
        A1["Mentor Agent<br/>Run"]
        A2["Designer Agent<br/>Run"]
        AN["Custom Agent<br/>Run"]
        GEMINI["Gemini API<br/>(Vertex AI)"]
    end

    subgraph "Async Infrastructure"
        PUBSUB["Cloud Pub/Sub"]
        SCHED["Cloud Scheduler"]
        SM["Secret Manager"]
    end

    subgraph "External Services"
        GITHUB["GitHub API<br/>+ Webhooks"]
        TG_API["Telegram<br/>Bot API"]
        OPP_SRC["Opportunity<br/>Sources (TBD)"]
    end

    %% User → Frontend
    WEB -->|"Static files"| HOSTING
    WEB -->|"Auth"| AUTH
    WEB -->|"REST API<br/>(Bearer token)"| API
    WEB -->|"Realtime<br/>listeners"| FS

    %% API → Services
    API --> CHAT_SVC
    API --> ORCH
    API --> GH_SVC
    API --> TG_SVC

    %% Webhooks
    GITHUB -->|"Webhook events"| WH
    TG_API -->|"Updates"| WH

    %% Webhook → Pub/Sub
    WH -->|"Publish"| PUBSUB
    PUBSUB -->|"Push"| GH_SVC
    PUBSUB -->|"Push"| OPP_SVC

    %% Scheduler
    SCHED -->|"Trigger"| PUBSUB

    %% Routing and concurrent agent runs
    CHAT_SVC --> ROUTER
    GH_SVC --> ROUTER
    OPP_SVC --> ROUTER
    ROUTER --> ORCH
    ORCH --> RUNTIME
    RUNTIME --> A1
    RUNTIME --> A2
    RUNTIME --> AN
    A1 --> GEMINI
    A2 --> GEMINI
    AN --> GEMINI

    %% Services → Decision
    GH_SVC --> DECISION
    OPP_SVC --> DECISION

    %% Decision → Notification
    DECISION -->|"If notify"| TG_SVC
    TG_SVC --> TG_API

    %% Services → Firestore
    API --> FS
    GH_SVC --> FS
    CHAT_SVC --> FS
    DECISION --> FS
    OPP_SVC --> FS
    ORCH --> FS
    RUNTIME --> FS

    %% Secrets
    GH_SVC -->|"Token"| SM
    TG_SVC -->|"Bot token"| SM

    %% Telegram
    TG --> TG_API

    %% Opportunity Sources
    OPP_SRC --> OPP_SVC
```

---

## 2. Request Flow (Frontend → Backend)

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant FE as Frontend (Next.js)
    participant FA as Firebase Auth
    participant API as Backend (FastAPI)
    participant FS as Firestore

    U->>FE: Action (e.g., update settings)
    FE->>FA: getIdToken()
    FA-->>FE: ID Token
    FE->>API: PATCH /api/v1/me<br/>Authorization: Bearer <token>
    API->>API: verify_id_token()
    API->>FS: Update user document
    FS-->>API: Success
    API-->>FE: 200 OK + updated profile
    
    Note over FE,FS: Realtime updates
    FS-->>FE: onSnapshot (user doc changed)
    FE->>U: UI updated
```

---

## 3. GitHub Activity Flow

```mermaid
sequenceDiagram
    participant GH as GitHub
    participant WH as Webhook Handler
    participant PS as Pub/Sub
    participant W as GitHub Worker
    participant R as Agent Router
    participant AI as Mentor Agent + Gemini
    participant DP as Decision Policy
    participant FS as Firestore
    participant TG as Telegram API

    GH->>WH: POST /webhooks/github<br/>(push/PR event)
    WH->>WH: Validate HMAC signature
    WH->>WH: Check dedup (processed_events)
    WH->>PS: Publish to github-events
    WH-->>GH: 200 OK

    PS->>W: Push delivery
    W->>W: Double-check dedup
    W->>FS: Load user context
    W->>GH: Fetch diff/content (if needed)
    W->>R: Resolve subscribed agent
    R-->>W: Mentor agentId + grants
    W->>AI: Analyze activity<br/>(agentId + runId)
    AI-->>W: Structured analysis<br/>(concept, proficiency, significance)
    W->>FS: Create observation
    W->>FS: Update skill scores
    W->>DP: Evaluate significance
    DP-->>W: Decision (notify/silent)
    W->>FS: Record decision
    
    alt Decision = notify
        W->>TG: Send notification
    end
    
    W->>FS: Write processed_events
    W-->>PS: ACK
```

---

## 4. Opportunity Discovery Flow

```mermaid
sequenceDiagram
    participant SC as Cloud Scheduler
    participant PS as Pub/Sub
    participant OW as Opportunity Worker
    participant SRC as Opportunity Sources
    participant R as Agent Router
    participant AI as Selected Agent + Gemini
    participant DP as Decision Policy
    participant FS as Firestore
    participant TG as Telegram API

    SC->>PS: Publish trigger
    PS->>OW: Push delivery

    OW->>SRC: Fetch articles/jobs/etc.
    SRC-->>OW: Content items

    loop For each user
        OW->>R: Resolve authorized discovery agent(s)
        R-->>OW: agentId + grants
        OW->>FS: Load permitted agent/workspace context
        OW->>AI: Evaluate relevance<br/>(agentId + runId)
        AI-->>OW: Relevance scores

        loop For each relevant item
            OW->>FS: Create observation
            OW->>DP: Evaluate significance
            DP-->>OW: Decision

            alt Decision = notify
                OW->>TG: Send notification
            end
        end
    end

    OW-->>PS: ACK
```

---

## 5. Unified Multi-Agent Chat Flow

```mermaid
sequenceDiagram
    participant U as User
    participant CH as Channel (Web/Telegram)
    participant API as Chat Service
    participant FS as Firestore
    participant RT as Agent Router
    participant ADK as Selected Agent Runtime
    participant GEM as Gemini

    U->>CH: Send message
    CH->>API: Message + channel info
    API->>RT: Resolve addressed agent(s)
    RT-->>API: agentId(s) + authorization grants
    API->>FS: Load permitted agent and workspace context
    API->>FS: Store user message
    API->>ADK: Message + scoped context<br/>(agentId + runId)
    ADK->>GEM: Reason with context
    GEM-->>ADK: Response
    ADK-->>API: Identified agent response
    API->>FS: Store agent message
    
    alt Channel = Web
        API-->>CH: HTTP Response
    else Channel = Telegram
        API->>CH: Telegram Bot sendMessage
    end
    
    Note over FS,CH: Frontend picks up<br/>new messages via<br/>Firestore onSnapshot
```

---

## 6. Concurrent Agent Execution Flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as Backend API
    participant O as Run Orchestrator
    participant PS as Pub/Sub
    participant A1 as Research Agent Worker
    participant A2 as Designer Agent Worker
    participant FS as Firestore

    U->>API: Assign two tasks to two agents
    API->>O: Create agent runs
    O->>FS: Persist queued run records
    par Research run
        O->>PS: Dispatch research run
        PS->>A1: Execute with agent config + grants
        A1->>FS: Publish progress and artifact
    and Design run
        O->>PS: Dispatch design run
        PS->>A2: Execute with agent config + grants
        A2->>FS: Publish progress and artifact
    end
    FS-->>U: Realtime statuses and outputs
```

Each run is isolated by `uid`, `agentId`, and `runId`. Agents share work only through explicit workspace artifacts or recorded handoffs.

---

## 7. Ownership Map

### Frontend Owns

| Area | Details |
|------|---------|
| **UI/UX** | Preserve the approved frontend and make only correctness or backend-connection changes behind it |
| **Firebase Auth (client)** | Sign-in flow, token management, provider setup |
| **Routing** | `/`, `/login`, `/onboarding`, `/dashboard`, `/agents`, `/runs/[runId]`, `/chat`, `/settings` |
| **Dashboard** | Preserve the existing shell, agent roster, chat canvas, navigation, layout, and styling; connect current controls to backend data |
| **Chat Widget** | Chat UI, message display, input handling |
| **Settings UI** | Profile form, integration toggles, link code display |
| **Firestore Listeners** | Realtime subscriptions for user data |
| **GitHub OAuth Redirect** | Initiate OAuth flow, handle callback redirect |
| **Responsive Behavior** | Preserve and validate the current mobile/tablet/desktop behavior without redesigning it |

### Backend Owns

| Area | Details |
|------|---------|
| **Auth Verification** | Firebase ID token validation on every request |
| **All Firestore Writes** | User profiles, observations, messages, decisions |
| **Business Logic** | Decision policy, skill update formula, event processing |
| **AI/Agents** | Runtime construction from agent configs, Gemini calls, tool grants, prompts |
| **Run Orchestration** | Routing, concurrency limits, lifecycle state, cancellation, retry isolation |
| **Agent Collaboration** | Shared artifact references and auditable agent-to-agent handoffs |
| **GitHub Integration** | OAuth token exchange, webhook registration, API calls |
| **Telegram Integration** | Bot commands, message sending, webhook handling |
| **Webhook Processing** | GitHub event validation, Telegram update parsing |
| **Pub/Sub** | Topic management, message publishing, worker processing |
| **Secret Management** | Token storage/retrieval via Secret Manager |
| **Opportunity Collection** | Source fetching, relevance analysis, scheduling |
| **Decision Policy** | Significance evaluation, threshold logic, escalation rules |

### Shared Contract Points

| Contract | Location | Owner |
|----------|----------|-------|
| REST API | `openapi.yaml`, `docs/API.md` | Both (agreed upon) |
| Firestore Schema | `docs/FIRESTORE.md` | Both (agreed upon) |
| Firebase Auth Token Format | Firebase SDK standard | Firebase |
| GitHub OAuth Redirect URL | Agreed in setup | Both |

---

## 8. Deployment Architecture

```mermaid
graph LR
    subgraph "Internet"
        USER["Users"]
        GH["GitHub"]
        TG["Telegram"]
    end

    subgraph "Google Cloud Project"
        subgraph "Firebase"
            FH["Firebase Hosting<br/>(CDN)"]
            FA["Firebase Auth"]
            FS["Cloud Firestore"]
        end

        subgraph "Cloud Run"
            CR["Backend Service<br/>(FastAPI container)"]
        end

        subgraph "Infrastructure"
            PS["Cloud Pub/Sub"]
            CS["Cloud Scheduler"]
            SM["Secret Manager"]
            VA["Vertex AI<br/>(Gemini API)"]
        end
    end

    USER -->|"HTTPS"| FH
    USER -->|"HTTPS"| CR
    GH -->|"Webhook"| CR
    TG -->|"Webhook"| CR
    
    FH -->|"Static files"| USER
    CR -->|"API calls"| FS
    CR -->|"Pub/Sub"| PS
    CR -->|"AI calls"| VA
    CR -->|"Secrets"| SM
    CS -->|"Trigger"| PS
    PS -->|"Push"| CR
```

---

## 9. Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend Framework | Next.js 14+ | React-based web framework |
| Frontend Language | TypeScript | Type-safe frontend code |
| Frontend Auth | Firebase Auth (client SDK) | User authentication |
| Frontend Hosting | Firebase Hosting | Static file CDN |
| Frontend Realtime | Firestore (client SDK) | `onSnapshot` listeners |
| Backend Framework | FastAPI | Python REST API |
| Backend Language | Python 3.11+ | Backend implementation |
| Backend Runtime | Cloud Run | Managed container hosting |
| Database | Cloud Firestore | NoSQL document database |
| AI Framework | Google ADK | Configurable agent runtime and tool orchestration |
| LLM | Gemini (Vertex AI) | Natural language understanding |
| Message Queue | Cloud Pub/Sub | Async event processing |
| Scheduler | Cloud Scheduler | Cron-like job scheduling |
| Secrets | Secret Manager | Secure credential storage |
| GitHub Auth | GitHub OAuth App | Repository access |
| Telegram | Telegram Bot API | User communication |
