# Frontend product-readiness plan

## Goal

Prepare the existing frontend for **Multiple Customizable Agents** while keeping the approved dashboard visually unchanged. Preserve its current layout, styling, roster, chat canvas, navigation, and interaction design; limit later implementation work to dead-code removal, internal architecture, state correctness, and backend integration.

**Terminology:** Agent is the single product and technical term across the UI, routes, frontend models, backend APIs, Firestore, and runtime. `agentId` is the stable identifier.

## Scope

### In

- Repository/configuration hygiene required for reproducible frontend builds.
- Dedicated agent summary/detail models and validated API DTOs.
- Atomic onboarding using the existing form fields and visual flow.
- Multiple agents in the existing dashboard roster.
- Per-agent one-to-one conversation isolation using the existing chat interface.
- Existing agent create, edit, duplicate, pause, and archive flows connected to real services.
- Focused data subscriptions, mutation feedback, tests, and verified dead-code cleanup.

### Out

- Any dashboard redesign, restyling, layout change, new panel, new rail element, or visual replacement.
- New dashboard widgets, activity indicators, unread badges, analytics surfaces, or navigation patterns.
- New agent customization fields that require expanding the approved UI.
- Autonomous orchestration or backend business logic in the frontend.
- Team workspaces, marketplace, billing, or a native mobile app.

## Review findings

- The dashboard is approved and should remain visually and structurally unchanged.
- The current `useChat` changes recipients on one conversation and does not load a separate thread when the selected agent changes.
- Non-local conversation listing is a fabricated `workspace-chat`, so remote conversation identity is not implemented.
- Onboarding marks the profile complete before first-agent creation, allowing partial completion.
- Imported `frontend/lib/` files and the environment example are ignored and therefore missing from a reproducible checkout.
- Data access is split inconsistently across Firestore listeners, REST services, localStorage, and duplicated hooks/converters.
- The type model is already multi-agent, but customization, transport validation, and feature-state boundaries are underspecified.
- Lint, TypeScript no-emit, and production build pass; automated tests are missing.
- Legacy dashboard CSS/assets and the unused `recharts` dependency remain from the earlier mentor-dashboard direction.

## Classification

- **KEEP:** the complete rendered dashboard experience—shell, roster, chat canvas, spacing, styling, navigation, component arrangement, and interaction design—plus Auth context, route guards, typed services, read-only Firestore principle, REST mutations, and stable `agentId` attribution.
- **CHANGE LATER:** service/data boundaries, route-backed selection state, conversation isolation, onboarding transaction safety, API validation, and backend wiring behind the existing UI.
- **REMOVE LATER:** verified unused assets/styles/dependencies, placeholder remote chat state, broad dashboard subscriptions on narrow routes, duplicate converters/catalogs, and backend-only frontend env entries.
- **MISSING:** dedicated agent summary/detail models, validated schemas for the existing agent fields, canonical selection state, per-agent threads, conversation list/create APIs, atomic onboarding, runtime validation, focused tests, and resource-level state.

## Target architecture

```text
Unchanged app routes, dashboard components, and styles
        ↓
Agent / Chat / Runs / Settings feature controllers
        ↓
resource-scoped query and mutation hooks
        ↓
validated agent models ↔ API/Firestore DTO mappers
        ↓
explicit adapter
  ├─ local development repository
  └─ Firebase Auth + Firestore reads + REST mutations
```

The selected agent and conversation ID must be first-class state. Switching agents loads that agent's isolated one-to-one thread in the existing chat canvas.

## Ordered implementation plan

1. Repair ignored-file and environment-template rules; validate runtime configuration and prevent accidental production local mode.
2. Split transport DTOs, agent summary/detail models, validated schemas for the existing customization fields, and create/update commands; add runtime decoders.
3. Consolidate feature repositories and hooks; make roster, agent, conversation, message, run, and integration state independently loadable and invalidatable.
4. Make onboarding draft-safe and atomic across workspace defaults and first-agent creation.
5. Implement real conversation list/create/select contracts and isolate one-to-one message history by agent.
6. Connect the existing dashboard rail, chat canvas, and current controls to the new hooks/services without changing their rendered design.
7. Connect the existing agent form and lifecycle controls to validated backend mutations without adding new UI sections or fields.
8. Add focused unit/component/integration coverage, then remove only legacy code proven unused.
9. Verify lint, TypeScript, build, auth/onboarding recovery, agent switching, thread isolation, lifecycle actions, and desktop/mobile flows before rollout.

## Constraints

- Treat the current dashboard UI as frozen: no visual redesign, layout restructuring, new widgets, new rail elements, or styling overhaul.
- Preserve existing component markup and CSS classes wherever backend wiring does not require a correctness fix.
- Firebase Auth remains client-side and Firestore access remains read-only from the browser.
- All mutations go through services and backend APIs, including when a local adapter supplies development behavior.
- Do not put backend secrets in frontend environment files.
- Keep TypeScript strict and avoid unvalidated external data at domain boundaries.
- Keep `/agents` and `/agents/[agentId]` as the canonical management routes.

## Validation gate

- ESLint and TypeScript no-emit.
- Next.js production build in explicit remote and local configurations.
- Automated coverage for DTO validation, onboarding recovery, agent switching, message isolation, retry, and lifecycle mutations.
- Before/after screenshot comparison confirming the dashboard is visually unchanged.
- Manual browser inspection of authentication, onboarding, conversation switching, agent management, settings, and existing error/empty states.

## Source review

See [`frontend/docs/2026-08-29-multiple-agents-frontend-review.md`](../../2026-08-29-multiple-agents-frontend-review.md) for evidence, classifications, risks, and cleanup candidates.
