# Mark-I — Demo Script

> **Status:** Draft v1.1  
> **Last updated:** 2026-08-29  
> **Video length:** 4 minutes maximum  
> **Target audience:** Hackathon judges (Google Cloud / DevPost)

---

## Demo Objectives

The demo must prove:

1. **Multi-agent product** — Users create specialized agents instead of receiving one fixed assistant
2. **Parallel execution** — At least two differently configured agents work simultaneously
3. **Agentic behavior** — Agents act proactively, not just reactively
4. **Google Cloud usage** — Cloud Run, Vertex AI / Gemini, Pub/Sub, Firestore
5. **Control and transparency** — Every run has a visible owner, state, context boundary, and output

---

## Demo Script (4 minutes)

### Act 1 — The Problem (0:00 – 0:25)

> **Narration:** "One AI assistant is expected to mentor, research, design, and plan—one task and one mixed context at a time. Mark-I lets you create the specialized agents you need and run them together, simultaneously."

**Show:**
- Brief slide/visual of the problem
- Transition to the live product

---

### Act 2 — Create an Agent Workspace (0:25 – 1:05)

**Step 1: Sign In**
- Show Google sign-in on the website
- The existing dashboard appears in its current form

**Step 2: Set Workspace Goal**
- Set goal: "Take my product from concept to launch"
- Choose language and notification defaults

**Step 3: Create Specialized Agents**
- Create a mentor agent from the developer-growth template
- Create a designer agent from the product-design template
- Briefly show that each has separate instructions, tools, and context access

**Step 4: Show the Agent Roster**
- Mentor: GitHub access, proactive notifications, normal tone
- Designer: workspace brief access, artifact publishing, concise critique tone
- Both agents are active and independently configurable

> **Narration:** "These are not modes of one assistant. They are separate user-created agents with their own roles, instructions, access, and run histories."

---

### Act 3 — Parallel Agent Execution (1:05 – 2:10)

**Step 5: Assign Work**
- Ask the mentor agent to analyze the current implementation and propose a learning plan
- Ask the designer agent to produce an improved onboarding direction
- Start both assignments together

**Step 6: Show Concurrent Runs**
- Run timeline shows both agents as `running`
- Briefly show separate `agentId` and `runId` values in Cloud Run logs
- Mention that Pub/Sub dispatches isolated workers concurrently

**Step 7: Inspect Outputs**
- Mentor completes with an implementation/learning plan
- Designer completes with a product artifact
- Show that each output identifies its agent and originating run
- Show one explicit shared artifact or handoff between agents

> **Narration:** "Both agents worked at the same time. Their contexts stayed separate, their outputs stayed attributable, and collaboration happened through a visible handoff—not hidden shared memory."

---

### Act 4 — Proactive Mentor Agent (2:10 – 3:00)

**Step 8: Push Code**
- Push a prepared commit to the connected repository
- Show the webhook entering the event router and being assigned to the mentor agent

**Step 9: Analysis and Decision Policy**
- Ask the mentor agent about the latest GitHub activity in the existing chat
- The agent explains the skill update, observation, and notification reason in that conversation
- Narrate: "The mentor agent judges significance, while deterministic policy decides whether notification is allowed."

**Step 10: Telegram Notification**
- Switch to Telegram
- Show the notification: "📊 I noticed you worked on recursive tree traversal in PR #42. Your recursion skill improved to 4.5/10. The base case handling was solid — consider exploring tail recursion next."

> **Narration:** "Mentoring is one agent specialization inside Mark-I—not the whole product. The same workspace can host any specialist the user configures."

---

### Act 5 — Conversation + Cross-Channel (3:00 – 3:30)

**Step 11: Address a Specific Agent**
- In Telegram, ask the mentor agent: "What should I focus on next?"
- The response clearly identifies the mentor agent

**Step 12: Same Conversation on Web**
- Switch to web chat
- Show the same conversation visible on the website
- Address the designer agent in a new thread to demonstrate identity and context separation

> **Narration:** "The channel can change without losing agent identity, run ownership, or the correct context."

---

### Act 6 — Architecture + Wrap-up (3:30 – 4:00)

**Step 13: Architecture Diagram**
- Show the system architecture diagram
- Highlight Google Cloud components:
  - ☁️ Cloud Run (backend)
  - 🧠 Vertex AI / Gemini (AI reasoning)
  - 📨 Cloud Pub/Sub (async processing)
  - 🗄️ Cloud Firestore (database)
  - ⏰ Cloud Scheduler (opportunity discovery)
  - 🔐 Secret Manager (credential storage)

**Step 14: Closing**
> **Narration:** "Mark-I is your configurable multi-agent workspace. Create a mentor, designer, researcher, or any specialist you need—then let them work in parallel with clear context, control, and accountability. Built on Google Cloud."

---

## Google Cloud Services to Show

These MUST be visible in the demo to score well on "Technical Execution":

| Service | What to Show | When |
|---------|-------------|------|
| **Cloud Run** | Deployment dashboard, running service, logs | Act 3 + Act 6 |
| **Vertex AI / Gemini** | API call in logs, mention ADK | Act 3 |
| **Cloud Pub/Sub** | Topic/message in Cloud Console | Act 3 (briefly) |
| **Cloud Firestore** | Data in Console for optional backend verification | Optional |
| **Cloud Scheduler** | Cron job in Console | Act 6 (architecture) |
| **Secret Manager** | Mention in architecture | Act 6 |

---

## Bonus Points

| Bonus | Points | Effort |
|-------|--------|--------|
| Post on X/LinkedIn with #AllThingsAgenticHackathon | +0.2 | Low |
| Blog post about the experience | +0.2 | Medium |
| Show the first agent appearing in the existing dashboard roster | — | In demo |
| Show agent explaining a past decision in chat | — | In demo |

---

## Pre-Demo Checklist

- [ ] Test account created and clean
- [ ] GitHub test repo with prepared commits ready
- [ ] Telegram bot running, webhook active
- [ ] Backend deployed to Cloud Run, healthy
- [ ] Frontend deployed to Firebase Hosting
- [ ] Cloud Scheduler configured
- [ ] All secrets in Secret Manager
- [ ] Architecture diagram prepared (visual)
- [ ] Screen recording software ready
- [ ] 4-minute timer running during recording
- [ ] Cloud Console tabs open (Cloud Run, Vertex AI, Pub/Sub)

---

## Demo Recovery Plan

If something breaks during recording:

| Failure | Recovery |
|---------|----------|
| Webhook doesn't fire | Have a pre-recorded clip of webhook flow as backup |
| Gemini API timeout | Retry; have cached response ready |
| Telegram bot down | Show web chat only, mention Telegram integration |
| Dashboard doesn't update | Refresh page; Firestore listener may need reconnect |
| OAuth flow fails | Pre-connect GitHub before recording, skip OAuth demo |

---

## Things the Demo Must NOT Do

- ❌ Show raw code for more than 5 seconds (boring for judges)
- ❌ Show terminal/deployment process (not the product)
- ❌ Have long silent pauses
- ❌ Exceed 4 minutes
- ❌ Only show reactive behavior (must show proactive: notifications, opportunities)
- ❌ Hide the decision-making (must show transparency)
