# Mark-I — Product Requirements Document

> **Status:** Draft v1.1  
> **Last updated:** 2026-08-29  
> **Authors:** Yernur (backend/agent), Vlad (frontend)

---

## 1. Problem

People increasingly use AI across different parts of their work, but most assistants are still designed as one generic agent with one personality, one context, and one task at a time.

Current assistants and productivity tools are:
- **Passive** — they only show data when you ask for it
- **Generic** — one assistant is expected to mentor, design, research, plan, and execute equally well
- **Silent** — they never proactively suggest what to do next
- **Sequential** — users cannot easily assign several specialists and let them work at the same time
- **Disconnected** — each conversation loses the shared goal, artifacts, and progress of the wider workspace

There is no simple system where a user can create a personal roster of specialized AI agents, configure each one to a preferred role and style, and run several of them simultaneously toward a shared objective while retaining clear ownership and visibility.

---

## 2. Target User

**Builders, creators, and knowledge workers** who regularly switch between different modes of work and want specialist AI collaborators. The initial product remains developer-focused and integrates deeply with GitHub, but the product model supports broader roles such as design, research, planning, and critique.

They:
- Have one or more ongoing goals or projects
- Want different agents for different responsibilities
- Need multiple agents to make progress simultaneously
- Want control over each agent's instructions, tone, tools, and access
- Need proactive help without losing transparency or control

---

## 3. Product Vision

**Mark-I** is a configurable **multi-agent workspace**. Users create specialized agents, give each one a role, goal, behavior, tools, and context, then assign work to one agent or several at once.

An agent can be a mentor that observes GitHub activity, a designer that develops product directions, a researcher that gathers evidence, a planner that decomposes work, or a custom specialist defined by the user. Agents can:
- **Specialize** around a clear role and user-defined objective
- **Observe** connected activity and react proactively when permitted
- **Collaborate** through shared workspace context and explicit handoffs
- **Run concurrently** on independent or coordinated tasks
- **Report** status, decisions, outputs, and blockers in a unified workspace
- **Adapt** tone, intensity, tools, and notification behavior to user preferences

The mentor experience remains an important first template, not the boundary of the product.

---

## 4. Core Value Proposition

> "Create your own team of AI agents—mentor, designer, researcher, or any specialist you need—and let them work together at the same time, on your terms."

---

## 5. User Personas

### Persona A — "The Job Seeker" (Primary)

- **Name:** Alex, 22
- **Goal:** Land a first developer job in 3 months
- **Behavior:** Practices algorithms on GitHub, studies web dev
- **Pain:** Doesn't know which skills are strong enough and which need work
- **Wants:** Daily check-ins, relevant job postings, skill gap analysis
- **Intensity:** Normal or Brutal

### Persona B — "The Learner" (Secondary)

- **Name:** Dana, 28
- **Goal:** Transition from frontend to full-stack
- **Behavior:** Building side projects, exploring backend concepts
- **Pain:** Lacks structure, doesn't know what to learn next
- **Wants:** Weekly insights, relevant articles/tutorials, progress tracking
- **Intensity:** Chill or Normal

### Persona C — "The Multi-disciplinary Builder" (Primary)

- **Name:** Sam, 26
- **Goal:** Take a product from idea to working launch
- **Behavior:** Alternates between product strategy, coding, design, research, and communication
- **Pain:** A single general-purpose assistant mixes contexts and becomes a bottleneck
- **Wants:** A mentor agent, product designer agent, and research agent working in parallel with visible progress
- **Control needs:** Separate instructions and tool access for every agent

---

## 6. User Journeys

### Journey 1 — Onboarding

```
User visits Mark-I website
    → Signs in (Google / GitHub / Email)
    → Sees onboarding wizard
    → Sets workspace goal, preferred language, and default notification behavior
    → Creates a first agent from a template or from scratch
    → Configures its name, role, instructions, tone, tools, and context access
    → Connects GitHub via OAuth
    → Generates Telegram link code
    → Sends /start to bot, then /link <code>
    → Telegram linked, dashboard populated
    → The agent becomes available in the workspace
```

### Journey 2 — Build an Agent Roster

```
User opens the agents workspace
    → Creates a mentor agent from the developer-growth template
    → Creates a designer agent from the product-design template
    → Creates a custom research agent
    → Reviews each agent's goal, tools, memory scope, and notification policy
    → Sees all active agents and their current status in one place
```

### Journey 3 — Parallel Execution

```
User defines a product objective
    → Assigns competitor research to the research agent
    → Assigns experience concepts to the designer agent
    → Assigns an implementation learning plan to the mentor agent
    → Mark-I starts independent runs concurrently
    → Agents publish progress and artifacts to the workspace
    → User reviews outputs or asks agents to hand work to one another
```

### Journey 4 — GitHub Activity Loop (Mentor Template)

```
User pushes code to connected repo
    → GitHub webhook fires
    → Backend receives event via Pub/Sub
    → Event router assigns it to the configured mentor agent
    → Gemini analyzes diff/PR content using that agent's configuration
    → Observation created (concept, sentiment, summary)
    → Skill scores updated (weighted average)
    → Decision policy evaluates significance
    → If significant: Telegram notification sent
    → Dashboard reflects updated skills and observations
```

### Journey 5 — Opportunity Discovery

```
Cloud Scheduler triggers (hourly for demo, daily for prod)
    → Opportunity collector fetches from configured sources
    → Event router assigns evaluation to an agent with opportunity-discovery access
    → That agent evaluates relevance against its goal and permitted workspace context
    → If relevant: observation created, Telegram notification sent
    → Dashboard shows new opportunity
```

### Journey 6 — Conversational Interaction

```
User sends message (via Telegram or web chat)
    → Backend routes to unified chat service
    → User addresses one agent or a selected group
    → Runtime loads the addressed agent's configuration and permitted context
    → The agent reasons, optionally calls permitted tools or requests a handoff
    → Response sent back via same channel
    → Message history visible on both Telegram and web
```

### Journey 7 — Decision and Run Transparency

```
User wonders: "Why did this agent act, and what are the others doing?"
    → User opens the run timeline or asks in chat
    → Mark-I shows which agent acted, its trigger, tools used, status, and decision-policy reasoning
    → User can pause a run, change the assignment, or inspect the produced artifact
```

---

## 7. Features

### F1 — Authentication

| Field | Value |
|-------|-------|
| **ID** | F1 |
| **Name** | Firebase Authentication |
| **Description** | Multi-provider sign-in with Google, GitHub, and Email/Password via Firebase Auth. Backend verifies Firebase ID tokens on every request. |
| **User Story** | As a user, I want to sign in quickly with my Google/GitHub account so I don't need to create a new password. |
| **Acceptance Criteria** | 1. User can sign in with Google, GitHub, or Email/Password. 2. Backend rejects requests without valid Firebase ID token. 3. First sign-in creates `users/{uid}` in Firestore. |
| **Priority** | **MUST** |
| **Dependencies** | None |

### F2 — User Onboarding

| Field | Value |
|-------|-------|
| **ID** | F2 |
| **Name** | User Onboarding |
| **Description** | First-time setup wizard where users define their learning goal, intensity preference, and language. Stores profile in Firestore. |
| **User Story** | As a new user, I want to set my learning goal and communication intensity so the agent can personalize its behavior. |
| **Acceptance Criteria** | 1. Onboarding shown only on first sign-in (no profile exists). 2. User selects goal type. 3. User selects intensity (chill / normal / brutal). 4. Profile saved to Firestore `users/{uid}`. |
| **Priority** | **MUST** |
| **Dependencies** | F1 |

### F3 — Telegram Linking

| Field | Value |
|-------|-------|
| **ID** | F3 |
| **Name** | Telegram Account Linking |
| **Description** | User generates a temporary link code on the website, sends `/link <code>` to the Telegram bot, which associates their Telegram user ID with their Firebase UID. |
| **User Story** | As a user, I want to link my Telegram account so the agent can message me directly. |
| **Acceptance Criteria** | 1. Website generates a unique 6-character code (TTL: 10 minutes). 2. User sends `/link <code>` to bot. 3. Bot validates code and links `telegramUserId` to `uid`. 4. Bot confirms successful linking. 5. Expired/invalid codes are rejected with clear error. |
| **Priority** | **MUST** |
| **Dependencies** | F1 |

### F4 — GitHub Integration

| Field | Value |
|-------|-------|
| **ID** | F4 |
| **Name** | GitHub OAuth + Webhook Setup |
| **Description** | User connects GitHub via OAuth. Backend obtains an access token, registers webhooks on selected repositories, and stores encrypted token reference. Supports multiple repos. |
| **User Story** | As a user, I want to connect my GitHub account and select repos so the agent can analyze my coding activity. |
| **Acceptance Criteria** | 1. OAuth flow with GitHub redirects back to app. 2. Backend receives and securely stores access token (Secret Manager). 3. User selects repos to monitor. 4. Webhooks registered on selected repos. 5. Multiple repos supported. 6. User can disconnect/reconnect. |
| **Priority** | **MUST** |
| **Dependencies** | F1 |

### F5 — GitHub Activity Analysis

| Field | Value |
|-------|-------|
| **ID** | F5 |
| **Name** | GitHub Activity Analysis |
| **Description** | When GitHub webhook events arrive (push, PR, review, issues, comments, etc.), Gemini analyzes the content and produces structured observations about concepts demonstrated, skill level shown, and sentiment. |
| **User Story** | As a user, I want the agent to understand what concepts I'm practicing when I code, so it can track my progress automatically. |
| **Acceptance Criteria** | 1. All supported GitHub event types are received and processed. 2. Gemini produces structured analysis (concept, proficiency assessment, sentiment). 3. Observation stored in Firestore. 4. Skill scores updated via weighted average formula. 5. Events are processed idempotently. |
| **Priority** | **MUST** |
| **Dependencies** | F4 |

### F6 — Skill Tracking

| Field | Value |
|-------|-------|
| **ID** | F6 |
| **Name** | Skill Score Tracking |
| **Description** | System maintains a map of skill → score (0-10) for each user. Updated via weighted average: `new = old * 0.7 + assessment * 0.3`. Skills are automatically discovered from GitHub analysis. |
| **User Story** | As a user, I want to see my proficiency level across different programming concepts so I can identify strengths and weaknesses. |
| **Acceptance Criteria** | 1. Skills auto-discovered from GitHub analysis. 2. Score 0-10 range, updated via weighted average. 3. Skill history is preserved (via observations). 4. Dashboard displays current skill levels. 5. Agent can reference skills in conversation. |
| **Priority** | **MUST** |
| **Dependencies** | F5 |

### F7 — Observation System

| Field | Value |
|-------|-------|
| **ID** | F7 |
| **Name** | Observation System |
| **Description** | Core data entity that records every meaningful event — GitHub analysis results, opportunity matches, and chat-derived insights. Each observation includes source, summary, concept, sentiment, significance score, and timestamps. |
| **User Story** | As a user, I want a feed of what the agent has noticed about my activity so I can understand its reasoning. |
| **Acceptance Criteria** | 1. Observations created from GitHub events, opportunities, and chat. 2. Each observation has source, summary, concept, sentiment, significance score. 3. Observations feed displayed on dashboard. 4. Observations used as context for agent reasoning. |
| **Priority** | **MUST** |
| **Dependencies** | F5 |

### F8 — Decision Policy

| Field | Value |
|-------|-------|
| **ID** | F8 |
| **Name** | Explicit Decision Policy |
| **Description** | Deterministic business logic (NOT in prompt) that decides whether to notify the user about an observation. Based on significance score, user intensity setting, and configurable thresholds. Must be transparent and explainable. |
| **User Story** | As a user, I want the agent to be smart about when it contacts me — not spam every commit, but alert me for important things. |
| **Acceptance Criteria** | 1. Decision is made by explicit Python code, not prompt. 2. Significance threshold varies by intensity: chill=7, normal=5, brutal=3. 3. Decision record stored in Firestore (what was decided and why). 4. Agent can explain any past decision when asked. 5. Special escalation rules: repeated errors, skill regression, new concept. |
| **Priority** | **MUST** |
| **Dependencies** | F7 |

### F9 — Opportunity Discovery

| Field | Value |
|-------|-------|
| **ID** | F9 |
| **Name** | Opportunity Discovery |
| **Description** | Scheduled collector fetches content from configured sources and routes it to an authorized agent, which evaluates relevance against its objective and permitted workspace context and creates observations for relevant matches. |
| **User Story** | As a user, I want the agent to find relevant articles, jobs, and challenges that match my goal and current skill level. |
| **Acceptance Criteria** | 1. Cloud Scheduler triggers collection (hourly for demo). 2. Sources fetched and parsed. 3. Gemini evaluates relevance per user. 4. Relevant items create observations. 5. Decision policy determines notification. |
| **Priority** | **MUST** |
| **Dependencies** | F2, F6 |

### F10 — Unified Chat

| Field | Value |
|-------|-------|
| **ID** | F10 |
| **Name** | Unified Chat (Telegram + Web) |
| **Description** | One conversation service handles Telegram and web while preserving agent identity, thread context, and channel continuity. Users can address one agent or a group. |
| **User Story** | As a user, I want to talk to any of my agents from web or Telegram without losing who is responsible or what context is active. |
| **Acceptance Criteria** | 1. Chat works from both Telegram and web. 2. Each message and thread records the addressed `agentId` values. 3. The selected agent receives only its permitted context plus explicitly shared workspace context. 4. Agent identity is visible in every response. 5. Conversation history remains continuous across channels. |
| **Priority** | **MUST** |
| **Dependencies** | F1, F3 |

### F11 — Dashboard

| Field | Value |
|-------|-------|
| **ID** | F11 |
| **Name** | Dashboard |
| **Description** | Main workspace showing the agent roster, active and queued runs, recent outputs, observations, and explainable decisions. Mentor-specific skill views appear when that template is enabled. |
| **User Story** | As a user, I want to see what every agent is doing, what it produced, and where my attention is needed. |
| **Acceptance Criteria** | 1. Agent roster with role and live status. 2. Active, queued, completed, failed, and paused runs are visible. 3. Outputs and decisions identify their owning agent. 4. Mentor skill visualization remains available. 5. Real-time updates and responsive design. |
| **Priority** | **MUST** |
| **Dependencies** | F6, F7, F8 |

### F12 — Notifications

| Field | Value |
|-------|-------|
| **ID** | F12 |
| **Name** | Telegram Notifications |
| **Description** | When decision policy determines a notification is warranted, send a formatted message to the user's linked Telegram account. |
| **User Story** | As a user, I want to receive Telegram messages when something important happens with my coding progress. |
| **Acceptance Criteria** | 1. Notifications sent only when decision policy approves. 2. Messages are well-formatted (Markdown). 3. Messages include context (what happened, why it matters). 4. Notifications respect intensity setting. 5. If Telegram is not linked, notification is stored but not sent. |
| **Priority** | **MUST** |
| **Dependencies** | F3, F8 |

### F13 — Settings

| Field | Value |
|-------|-------|
| **ID** | F13 |
| **Name** | Settings Page |
| **Description** | Frontend area for managing workspace defaults, integrations, and every agent's role, instructions, tone, tools, context access, and notification policy. |
| **User Story** | As a user, I want precise control over how each agent behaves and what it can access. |
| **Acceptance Criteria** | 1. Create, edit, duplicate, pause, and archive agents. 2. Configure role, instructions, tone, tools, context scope, and notifications independently. 3. Manage GitHub and Telegram integrations. 4. Show the impact of permission changes. 5. Updates affect new runs immediately. |
| **Priority** | **MUST** |
| **Dependencies** | F1, F2 |

### F14 — Decision Transparency UI

| Field | Value |
|-------|-------|
| **ID** | F14 |
| **Name** | Decision Transparency |
| **Description** | Dashboard block showing recent agent decisions: "notified because X" or "stayed silent because Y". Powerful demo element. |
| **User Story** | As a user, I want to understand why the agent decided to notify me or stay silent about specific events. |
| **Acceptance Criteria** | 1. Dashboard shows last N decisions with explanations. 2. Each decision shows: trigger, significance score, threshold, action taken, reason. 3. User can ask agent about any decision in chat. |
| **Priority** | **SHOULD** |
| **Dependencies** | F8, F11 |

### F15 — Agent Identity and Behavior

| Field | Value |
|-------|-------|
| **ID** | F15 |
| **Name** | Configurable Agent Identity and Behavior |
| **Description** | Every agent has a stable name, role, objective, instructions, tone, and visual identity. Chill, normal, and brutal remain optional tone presets. |
| **User Story** | As a user, I want each agent to feel and behave like the specialist I created. |
| **Acceptance Criteria** | 1. Identity and behavior are stored per agent. 2. Templates provide editable defaults. 3. Tone affects communication, not authorization or deterministic policy. 4. Responses and outputs clearly identify the agent. |
| **Priority** | **SHOULD** |
| **Dependencies** | F2, F10 |

### F16 — Agent Management

| Field | Value |
|-------|-------|
| **ID** | F16 |
| **Name** | Create and Manage Multiple Agents |
| **Description** | Users can create multiple specialized agents from templates or from scratch and manage their lifecycle independently. |
| **User Story** | As a user, I want a personal roster of specialists instead of one fixed assistant. |
| **Acceptance Criteria** | 1. Create from template or blank configuration. 2. Multiple agents per user. 3. Edit, duplicate, pause, and archive without affecting other agents. 4. Templates include Mentor and Designer; custom roles are supported. 5. Stable `agentId` is used across runs, messages, decisions, and outputs. |
| **Priority** | **MUST** |
| **Dependencies** | F1, F2 |

### F17 — Concurrent Multi-Agent Runs

| Field | Value |
|-------|-------|
| **ID** | F17 |
| **Name** | Concurrent Run Orchestration |
| **Description** | The runtime can execute independent assignments for multiple agents simultaneously while enforcing per-user limits and isolation. |
| **User Story** | As a user, I want my specialists to make progress in parallel instead of waiting for one assistant to finish everything sequentially. |
| **Acceptance Criteria** | 1. A user can start at least two agent runs concurrently. 2. Every run has owner, assignment, status, timestamps, and output references. 3. Failures and cancellation are isolated to one run. 4. Per-user concurrency and rate limits are enforced. 5. Status updates appear in real time. |
| **Priority** | **MUST** |
| **Dependencies** | F16 |

### F18 — Context, Tools, and Handoffs

| Field | Value |
|-------|-------|
| **ID** | F18 |
| **Name** | Scoped Context and Collaboration |
| **Description** | Agents receive only permitted tools and context. They collaborate through explicit shared artifacts and traceable handoffs rather than unrestricted hidden memory. |
| **User Story** | As a user, I want agents to collaborate without mixing private context or losing accountability. |
| **Acceptance Criteria** | 1. Tool and context permissions are stored per agent. 2. Workspace context is distinct from agent-private context. 3. Handoffs identify sender, receiver, purpose, and artifact. 4. Users can inspect and revoke access. 5. Tool calls and handoffs are auditable. |
| **Priority** | **MUST** |
| **Dependencies** | F16, F17 |

### F19 — Run Timeline and Controls

| Field | Value |
|-------|-------|
| **ID** | F19 |
| **Name** | Multi-Agent Run Visibility |
| **Description** | A unified timeline shows concurrent run progress, decisions, artifacts, failures, and requests for user input. |
| **User Story** | As a user, I want to understand and control what all my agents are doing at the same time. |
| **Acceptance Criteria** | 1. Timeline can be filtered by agent and status. 2. Users can pause or cancel active work. 3. Runs surface blockers and approval requests. 4. Outputs link back to the originating run. 5. No agent can impersonate another in the UI. |
| **Priority** | **MUST** |
| **Dependencies** | F11, F17 |

---

## 8. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Response time for chat | < 5 seconds |
| NFR-2 | Webhook processing time | < 30 seconds end-to-end |
| NFR-3 | Dashboard load time | < 3 seconds |
| NFR-4 | Concurrent users (hackathon) | 10-50 |
| NFR-5 | Data security | GitHub tokens in Secret Manager, not Firestore |
| NFR-6 | Uptime during hackathon demo | 99%+ |
| NFR-7 | Agent language | Auto-detect from user message |
| NFR-8 | Concurrent agent runs | At least 2 per user for MVP |
| NFR-9 | Run isolation | One agent failure must not terminate unrelated runs |
| NFR-10 | Identity traceability | Every message, action, decision, and artifact carries `agentId` and `runId` |

---

## 9. MVP Scope

### In Scope (MVP)

- F1 Authentication (Google + GitHub + Email/Password)
- F2 User Onboarding
- F3 Telegram Linking
- F4 GitHub Integration (OAuth, multiple repos)
- F5 GitHub Activity Analysis
- F6 Skill Tracking
- F7 Observation System
- F8 Decision Policy
- F9 Opportunity Discovery (sources TBD)
- F10 Unified Chat
- F11 Dashboard
- F12 Notifications
- F13 Settings
- F16 Agent Management
- F17 Concurrent Multi-Agent Runs
- F18 Context, Tools, and Handoffs
- F19 Run Timeline and Controls

### Should Have

- F14 Decision Transparency UI
- F15 Agent Identity and Behavior

### Out of Scope

- Mobile app
- Email notifications
- Payment/subscription
- Admin panel
- Multi-tenant/team features
- CI/CD activity analysis
- LeetCode integration
- Custom notification schedules
- Offline mode
- Autonomous cross-agent delegation without user-configured permissions

---

## 10. Future / Bonus Features

- Social media posts about the project (#AllThingsAgenticHackathon for +0.2)
- Blog post about the experience (+0.2)
- LeetCode integration
- Analytics / insights over time (weekly/monthly reports)
- Custom opportunity sources
- Team/group features
- Notification schedule preferences
- Community agent template marketplace
- Shared human teams and organization workspaces
- Advanced dependency graphs and autonomous multi-stage delegation

---

## 11. Success Criteria

### Hackathon Judging Criteria (from DevPost rules)

1. **Agentic AI Innovation** — How creatively the agent uses Google AI tools
2. **Technical Execution** — Quality of implementation using Google Cloud
3. **Impact & Usefulness** — Real-world value to developers
4. **UX/Design** — Polished, intuitive experience
5. **Presentation** — Clear 4-minute demo video

### Demo Must Show

- Complete user lifecycle (sign in → create agents → assign work → inspect parallel outputs)
- At least two differently configured agents running simultaneously
- A proactive mentor agent reacting to developer activity
- Clear agent identity, run ownership, and a visible handoff or shared artifact
- Decision policy transparency ("why I notified / why I stayed silent")
- Cross-channel interaction (same conversation on Telegram and web)
- Google Cloud services in action (Cloud Run, Vertex AI, Pub/Sub)

### Technical Must Show

- Cloud Run dashboard / deployment
- Vertex AI / Gemini API logs
- Pub/Sub message flow (if time)
- Architecture diagram

---

## 12. Hackathon Demo Requirements

See [DEMO.md](DEMO.md) for the complete demo script.

Key constraints:
- **4-minute video** maximum
- Must show Google Cloud usage prominently
- Must demonstrate agentic behavior (proactive, not just reactive)
- Must be reproducible (README with setup instructions)
