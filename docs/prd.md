# Mark-I — Product Requirements Document

> **Status:** Draft v1.0  
> **Last updated:** 2026-08-19  
> **Authors:** Yernur (backend/agent), Vlad (frontend)

---

## 1. Problem

Developers learning new skills lack **proactive, contextual feedback** on their growth trajectory.

Current tools (GitHub stats, LeetCode streaks, learning platforms) are:
- **Passive** — they only show data when you ask for it
- **Generic** — not personalized to the user's goal
- **Silent** — they never proactively suggest what to do next
- **Disconnected** — skill progress, coding activity, and opportunities exist in separate silos

There is no system that continuously **watches** a developer's activity, **analyzes** their strengths and weaknesses, **discovers** relevant opportunities, and **proactively communicates** actionable insights — all personalized to a stated goal.

---

## 2. Target User

**Junior-to-mid developers** who are actively learning and improving, specifically those who:
- Have a defined learning goal (e.g., "get a job", "master algorithms", "learn a new stack")
- Use GitHub for coding practice or real projects
- Use Telegram as a daily messenger
- Want proactive guidance, not just passive tracking

---

## 3. Product Vision

**Mark-I** is an AI-powered **developer growth agent** — a personal mentor that:
- **Observes** the developer's GitHub activity in real-time
- **Tracks** skill progression across concepts and technologies
- **Discovers** relevant opportunities (articles, jobs, challenges)
- **Decides** when and how to communicate based on significance and user preferences
- **Converses** naturally through Telegram and web, with full context awareness

The agent operates like a thoughtful mentor — it doesn't spam every commit, but it notices patterns, flags regressions, celebrates improvements, and surfaces the right opportunity at the right time.

---

## 4. Core Value Proposition

> "An AI agent that watches your code, tracks your growth, finds relevant opportunities, and proactively mentors you through Telegram — knowing when to speak and when to stay silent."

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

---

## 6. User Journeys

### Journey 1 — Onboarding

```
User visits Mark-I website
    → Signs in (Google / GitHub / Email)
    → Sees onboarding wizard
    → Sets goal, intensity, preferred language
    → Connects GitHub via OAuth
    → Generates Telegram link code
    → Sends /start to bot, then /link <code>
    → Telegram linked, dashboard populated
    → System begins monitoring
```

### Journey 2 — GitHub Activity Loop

```
User pushes code to connected repo
    → GitHub webhook fires
    → Backend receives event via Pub/Sub
    → Gemini analyzes diff/PR content
    → Observation created (concept, sentiment, summary)
    → Skill scores updated (weighted average)
    → Decision policy evaluates significance
    → If significant: Telegram notification sent
    → Dashboard reflects updated skills and observations
```

### Journey 3 — Opportunity Discovery

```
Cloud Scheduler triggers (hourly for demo, daily for prod)
    → Opportunity collector fetches from configured sources
    → Gemini evaluates relevance against user's goal and skill profile
    → If relevant: observation created, Telegram notification sent
    → Dashboard shows new opportunity
```

### Journey 4 — Conversational Interaction

```
User sends message (via Telegram or web chat)
    → Backend routes to unified chat service
    → ADK agent receives message + full user context
    → Agent reasons, optionally calls tools
    → Response sent back via same channel
    → Message history visible on both Telegram and web
```

### Journey 5 — Decision Transparency

```
User wonders: "Why did the agent notify me about this but not that?"
    → User asks agent in chat
    → Agent explains decision policy reasoning
    → Dashboard shows "why" block next to each decision
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
| **Description** | Scheduled collector fetches content from configured sources, Gemini evaluates relevance against user's goal and skill profile, creates observations for relevant matches. |
| **User Story** | As a user, I want the agent to find relevant articles, jobs, and challenges that match my goal and current skill level. |
| **Acceptance Criteria** | 1. Cloud Scheduler triggers collection (hourly for demo). 2. Sources fetched and parsed. 3. Gemini evaluates relevance per user. 4. Relevant items create observations. 5. Decision policy determines notification. |
| **Priority** | **MUST** |
| **Dependencies** | F2, F6 |

### F10 — Unified Chat

| Field | Value |
|-------|-------|
| **ID** | F10 |
| **Name** | Unified Chat (Telegram + Web) |
| **Description** | Single chat service handles both Telegram and web messages. Same ADK agent, same conversation history. User can switch between channels seamlessly. |
| **User Story** | As a user, I want to chat with the agent on both Telegram and the website and see the same conversation history. |
| **Acceptance Criteria** | 1. Chat works from both Telegram and web. 2. Same conversation history visible on both channels. 3. Agent has access to full user context (skills, observations, goal). 4. Agent responds in user's language (auto-detect). 5. Messages stored in Firestore `users/{uid}/messages`. |
| **Priority** | **MUST** |
| **Dependencies** | F1, F3 |

### F11 — Dashboard

| Field | Value |
|-------|-------|
| **ID** | F11 |
| **Name** | Dashboard |
| **Description** | Main frontend view showing skill radar/bars, observation feed, recent decisions with explanations, and quick stats. Real-time updates via Firestore listeners. |
| **User Story** | As a user, I want a dashboard that shows my progress, recent activity, and agent decisions at a glance. |
| **Acceptance Criteria** | 1. Skill visualization (bars or radar chart). 2. Observation feed (filterable by source). 3. Decision log with "why" explanations. 4. Real-time updates (Firestore onSnapshot). 5. Responsive design. |
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
| **Description** | Frontend page for managing profile: goal, intensity, connected repos, Telegram link status, language preference. |
| **User Story** | As a user, I want to change my goal, intensity, and connected repos at any time. |
| **Acceptance Criteria** | 1. Display and edit goal. 2. Display and change intensity. 3. Show connected GitHub repos, allow disconnect/add. 4. Show Telegram link status, allow re-linking. 5. Changes immediately reflected in agent behavior. |
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

### F15 — Intensity Personas

| Field | Value |
|-------|-------|
| **ID** | F15 |
| **Name** | Intensity-based Agent Persona |
| **Description** | Agent's communication style adapts to user's intensity setting: chill (encouraging, gentle), normal (balanced, informative), brutal (direct, challenging). |
| **User Story** | As a user, I want the agent's tone to match my preferred communication style. |
| **Acceptance Criteria** | 1. Three distinct personas in agent prompts. 2. Persona affects message tone, not decision logic. 3. Persona can be changed in settings and takes effect immediately. |
| **Priority** | **SHOULD** |
| **Dependencies** | F2, F10 |

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

### Should Have

- F14 Decision Transparency UI
- F15 Intensity Personas

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

---

## 10. Future / Bonus Features

- Social media posts about the project (#AllThingsAgenticHackathon for +0.2)
- Blog post about the experience (+0.2)
- LeetCode integration
- Analytics / insights over time (weekly/monthly reports)
- Custom opportunity sources
- Team/group features
- Notification schedule preferences

---

## 11. Success Criteria

### Hackathon Judging Criteria (from DevPost rules)

1. **Agentic AI Innovation** — How creatively the agent uses Google AI tools
2. **Technical Execution** — Quality of implementation using Google Cloud
3. **Impact & Usefulness** — Real-world value to developers
4. **UX/Design** — Polished, intuitive experience
5. **Presentation** — Clear 4-minute demo video

### Demo Must Show

- Complete user lifecycle (sign in → onboarding → activity → notification → conversation)
- Agent making autonomous decisions (not just responding to queries)
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

See [DEMO.md](file:///Users/macbook/Yernur/projects/Mark-I/docs/DEMO.md) for the complete demo script.

Key constraints:
- **4-minute video** maximum
- Must show Google Cloud usage prominently
- Must demonstrate agentic behavior (proactive, not just reactive)
- Must be reproducible (README with setup instructions)
