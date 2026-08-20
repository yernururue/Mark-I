# Mark-I — Demo Script

> **Status:** Draft v1.0  
> **Last updated:** 2026-08-19  
> **Video length:** 4 minutes maximum  
> **Target audience:** Hackathon judges (Google Cloud / DevPost)

---

## Demo Objectives

The demo must prove:

1. **Agentic behavior** — The agent acts proactively, not just reactively
2. **Google Cloud usage** — Cloud Run, Vertex AI / Gemini, Pub/Sub, Firestore
3. **Real-world value** — Solves a genuine developer pain point
4. **Technical quality** — Clean architecture, separation of concerns
5. **Decision transparency** — Agent explains its reasoning

---

## Demo Script (4 minutes)

### Act 1 — The Problem (0:00 – 0:30)

> **Narration:** "As developers, we have tools that track our activity — GitHub stats, LeetCode streaks — but none of them proactively mentor us. No tool watches our code, understands our growth, and decides when to reach out with the right insight at the right time. That's Mark-I."

**Show:**
- Brief slide/visual of the problem
- Transition to the live product

---

### Act 2 — Onboarding (0:30 – 1:15)

**Step 1: Sign In**
- Show Google sign-in on the website
- Dashboard appears (empty state)

**Step 2: Set Up Profile**
- Set goal: "Get a developer job"
- Set intensity: "Normal"
- Show the profile being saved

**Step 3: Connect GitHub**
- Click "Connect GitHub"
- OAuth flow completes
- Select a repo to monitor
- Show webhook confirmation

**Step 4: Link Telegram**
- Generate link code on website
- Switch to Telegram
- Send `/start` to the bot
- Send `/link ABC123`
- Bot confirms: "✅ Account linked! I'll start watching your coding activity."

> **Narration:** "In under a minute, Mark-I knows your goal, is watching your GitHub repos, and can reach you on Telegram."

---

### Act 3 — GitHub Activity → Agent Reaction (1:15 – 2:30)

**Step 5: Push Code**
- Show a commit being pushed to the connected repo
- Briefly show the code (something with recursion / data structures)

**Step 6: Behind the Scenes**
- Show Cloud Run logs: webhook received
- Show Pub/Sub message in Cloud Console (brief)
- Mention: "The event is processed asynchronously via Pub/Sub"

**Step 7: Agent Analysis**
- Show Vertex AI / Gemini API call in logs
- Narrate: "Gemini analyzes the diff and identifies concepts, proficiency level, and significance"

**Step 8: Observation + Skill Update**
- Dashboard shows new observation in feed
- Skill chart updates (recursion score changes)

**Step 9: Decision Policy**
- Show the decision log on dashboard: "Notified: significance 7 >= threshold 5 (normal intensity)"
- Narrate: "This is a deterministic decision policy — not a black box. The agent judges significance, but the notification decision is explicit code."

**Step 10: Telegram Notification**
- Switch to Telegram
- Show the notification: "📊 I noticed you worked on recursive tree traversal in PR #42. Your recursion skill improved to 4.5/10. The base case handling was solid — consider exploring tail recursion next."

> **Narration:** "The agent didn't just log a stat. It understood the code, assessed proficiency, and decided this was worth telling you about."

---

### Act 4 — Silence as a Decision (2:30 – 3:00)

**Step 11: Another Commit (trivial)**
- Push a small commit (typo fix / README update)
- Show: observation created but decision = "silent"
- Dashboard shows: "Stayed silent: significance 2 < threshold 5"

> **Narration:** "Mark-I knows when to stay quiet. A typo fix doesn't deserve a notification. This is what makes it a mentor, not a spambot."

---

### Act 5 — Conversation + Cross-Channel (3:00 – 3:30)

**Step 12: Ask the Agent (Telegram)**
- In Telegram: "What should I focus on next?"
- Agent responds with personalized advice based on skill profile

**Step 13: Same Conversation on Web**
- Switch to web chat
- Show the same conversation visible on the website
- Send a follow-up question from web

> **Narration:** "Same agent, same conversation, whether you're on Telegram or the web."

---

### Act 6 — Architecture + Wrap-up (3:30 – 4:00)

**Step 14: Architecture Diagram**
- Show the system architecture diagram
- Highlight Google Cloud components:
  - ☁️ Cloud Run (backend)
  - 🧠 Vertex AI / Gemini (AI reasoning)
  - 📨 Cloud Pub/Sub (async processing)
  - 🗄️ Cloud Firestore (database)
  - ⏰ Cloud Scheduler (opportunity discovery)
  - 🔐 Secret Manager (credential storage)

**Step 15: Closing**
> **Narration:** "Mark-I is an AI agent that watches your code, tracks your growth, discovers opportunities, and mentors you proactively — knowing when to speak and when to listen. Built entirely on Google Cloud."

---

## Google Cloud Services to Show

These MUST be visible in the demo to score well on "Technical Execution":

| Service | What to Show | When |
|---------|-------------|------|
| **Cloud Run** | Deployment dashboard, running service, logs | Act 3 + Act 6 |
| **Vertex AI / Gemini** | API call in logs, mention ADK | Act 3 |
| **Cloud Pub/Sub** | Topic/message in Cloud Console | Act 3 (briefly) |
| **Cloud Firestore** | Data in Console (optional, dashboard shows data) | Optional |
| **Cloud Scheduler** | Cron job in Console | Act 6 (architecture) |
| **Secret Manager** | Mention in architecture | Act 6 |

---

## Bonus Points

| Bonus | Points | Effort |
|-------|--------|--------|
| Post on X/LinkedIn with #AllThingsAgenticHackathon | +0.2 | Low |
| Blog post about the experience | +0.2 | Medium |
| Include before/after demo (empty → populated dashboard) | — | In demo |
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
