# Mark-I — Architecture Document

> **Status:** Draft v1.0  
> **Last updated:** 2026-08-19

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
        DECISION["Decision<br/>Policy Engine"]
        GH_SVC["GitHub<br/>Service"]
        TG_SVC["Telegram<br/>Service"]
        OPP_SVC["Opportunity<br/>Service"]
    end

    subgraph "AI Layer"
        ADK["ADK Agent"]
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

    %% Services → AI
    CHAT_SVC --> ADK
    GH_SVC --> ADK
    OPP_SVC --> ADK
    ADK --> GEMINI

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
    participant AI as ADK + Gemini
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
    W->>AI: Analyze activity
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
    participant AI as ADK + Gemini
    participant DP as Decision Policy
    participant FS as Firestore
    participant TG as Telegram API

    SC->>PS: Publish trigger
    PS->>OW: Push delivery

    OW->>SRC: Fetch articles/jobs/etc.
    SRC-->>OW: Content items

    loop For each user
        OW->>FS: Load user (goal, skills)
        OW->>AI: Evaluate relevance<br/>(items + user context)
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

## 5. Unified Chat Flow

```mermaid
sequenceDiagram
    participant U as User
    participant CH as Channel (Web/Telegram)
    participant API as Chat Service
    participant FS as Firestore
    participant ADK as ADK Agent
    participant GEM as Gemini

    U->>CH: Send message
    CH->>API: Message + channel info
    API->>FS: Load user context<br/>(profile, skills, observations)
    API->>FS: Store user message
    API->>ADK: Message + full context
    ADK->>GEM: Reason with context
    GEM-->>ADK: Response
    ADK-->>API: Agent response
    API->>FS: Store agent message
    
    alt Channel = Web
        API-->>CH: HTTP Response
    else Channel = Telegram
        API->>CH: Telegram Bot sendMessage
    end
    
    Note over FS,CH: Frontend picks up<br/>new messages via<br/>Firestore onSnapshot
```

---

## 6. Ownership Map

### Frontend Owns

| Area | Details |
|------|---------|
| **UI/UX** | All visual components, layouts, styling |
| **Firebase Auth (client)** | Sign-in flow, token management, provider setup |
| **Routing** | `/`, `/login`, `/onboarding`, `/dashboard`, `/chat`, `/settings` |
| **Dashboard** | Skill visualization, observation feed, decision log |
| **Chat Widget** | Chat UI, message display, input handling |
| **Settings UI** | Profile form, integration toggles, link code display |
| **Firestore Listeners** | Realtime subscriptions for user data |
| **GitHub OAuth Redirect** | Initiate OAuth flow, handle callback redirect |
| **Responsive Design** | Mobile/tablet/desktop layouts |

### Backend Owns

| Area | Details |
|------|---------|
| **Auth Verification** | Firebase ID token validation on every request |
| **All Firestore Writes** | User profiles, observations, messages, decisions |
| **Business Logic** | Decision policy, skill update formula, event processing |
| **AI/Agent** | ADK agent setup, Gemini calls, tool definitions, prompts |
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

## 7. Deployment Architecture

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

## 8. Technology Stack Summary

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
| AI Framework | Google ADK | Agent orchestration |
| LLM | Gemini (Vertex AI) | Natural language understanding |
| Message Queue | Cloud Pub/Sub | Async event processing |
| Scheduler | Cloud Scheduler | Cron-like job scheduling |
| Secrets | Secret Manager | Secure credential storage |
| GitHub Auth | GitHub OAuth App | Repository access |
| Telegram | Telegram Bot API | User communication |
