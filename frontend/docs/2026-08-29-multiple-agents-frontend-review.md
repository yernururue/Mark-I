# Multiple Customizable Agents — frontend review

**Date:** 2026-08-29  
**Scope:** `frontend/` and frontend-facing shared documentation  
**Constraint:** Review and planning only; no application/source code changed

## Executive summary

The current dashboard is already the approved product UI. Its shell, left-hand roster, chat canvas, layout, styling, navigation, and interaction design should remain visually unchanged. The work is architectural cleanup and backend integration, not a redesign.

The main risk is that the UI looks multi-agent while chat still behaves as one mutable workspace conversation. Selecting another agent changes the recipients of the same conversation and leaves the same message history on screen. That is incompatible with distinct agents and can mix identities and context. The other release-blocking issue is repository hygiene: the imported `frontend/lib/` modules are ignored by the root `.gitignore`, so a fresh clone can omit code required to build.

The recommended direction is an internal refactor behind the existing dashboard: keep **agent** as the single domain term, make agent selection and conversation identity correct, remove dead code, and connect the current controls to real backend services without adding or redesigning UI.

## 1. Current frontend architecture

```text
Next.js App Router routes
        ↓
client pages + components
        ↓
feature hooks using local React state/effects
        ↓
typed service modules
        ↓
local mode: localStorage adapter + simulated runs/chat
remote mode: Firebase Auth + Firestore read listeners + REST mutations
```

- **Framework:** Next.js 16.3, React 19, TypeScript strict mode.
- **UI:** one global CSS file with Tailwind 4 imported for base/build processing; Lucide icons.
- **Authentication:** Firebase Auth in a single React context; guarded application and onboarding routes.
- **Routes:** landing, login, onboarding, chat-first dashboard, agents list/detail, run detail, settings, and GitHub callback. `/chat` is a compatibility redirect to `/dashboard`.
- **State:** component-local state plus four independent hooks. There is no shared server-state cache or normalized domain store.
- **Data:** a `local` mode persists preview data in `localStorage`; a mode named `firebase` combines Firestore reads with REST writes.
- **Domain:** a single `types/models.ts` file contains profiles, agents, runs, artifacts, handoffs, observations, decisions, conversations, messages, and integrations.

## 2. Findings and technical debt

### Critical / high priority

1. **Required frontend modules are ignored by Git.** Root `.gitignore` line 28 ignores every directory named `lib/`, including `frontend/lib/api.ts`, `config.ts`, `errors.ts`, `firebase.ts`, and `id.ts`. They are imported throughout the tracked application but absent from `git ls-files`. The build succeeds only because those ignored files exist locally. The ignored `.env.local.example` also cannot serve as a committed setup template.

2. **Switching agents does not switch conversations.** `useChat` loads the first conversation once, and `selectAgents` updates recipients on that same conversation without loading a different history (`hooks/useChat.ts`, lines 38–71). Messages from the previous selection stay visible. Distinct agents need isolated one-to-one threads.

3. **The remote conversation layer is a placeholder, not a real contract.** In non-local mode, `getConversations` returns a fabricated `workspace-chat` object instead of calling the backend (`services/chat.ts`, lines 42–55). `updateRecipients` mutates that client object. The API can therefore send messages, but cannot reliably list, create, select, or persist agent-specific conversations.

4. **Onboarding can complete without creating the first agent.** The profile is marked complete before agent creation (`app/onboarding/page.tsx`, lines 128–137). If the second request fails and the page reloads, the route guard can redirect the user away from onboarding with an empty roster. Completion must be atomic or finalized only after the first agent exists.

5. **Runtime-critical configuration silently falls back to preview mode.** Any value other than the exact string `firebase` selects `local` mode (`lib/config.ts`, lines 1–10). A missing production variable can silently deploy a browser-only demo rather than fail fast.

### Medium priority

6. **The dashboard data boundary is too broad.** `subscribeDashboard` opens seven Firestore listeners and waits for all seven before first render (`services/dashboard.ts`, lines 173–199). Agent and run pages reuse this hook even when they need only a roster or one run. This increases cost, couples unrelated failures, and makes loading/error state coarse.

7. **State access is inconsistent and duplicated.** `useAgentRoster`, `useChat`, and `useDashboardData` each fetch the roster differently. Profile conversion exists in both `services/user.ts` and `services/dashboard.ts`. Local and remote paths do not share a single repository interface, invalidation strategy, or runtime schema validation.

8. **Types model transport data, UI state, and write inputs together.** `CreateAgentInput` is derived directly from `Agent`, raw string arrays represent permissions, and API JSON is trusted via casts. There are no dedicated summary/detail models, customization model, runtime DTO validation, schema/version field, or separate create/update command.

9. **Current customization logic is duplicated.** Onboarding and `AgentForm` maintain separate hardcoded template/permission lists. Selecting a template in `AgentForm` changes only its enum and does not apply template defaults. The existing fields need one shared catalog and validated backend contracts; new visual fields are not required.

10. **The dashboard subscribes to data it does not render.** The dashboard route renders only `ChatPanel`, while the dashboard snapshot also loads runs, artifacts, handoffs, observations, and decisions. Remove or narrow those unused subscriptions; do not add dashboard surfaces merely to justify them.

11. **Agent selection is not canonical route state.** Roster selection is not consistently reflected in the URL, so refresh/deep-link behavior differs between local and remote modes.

12. **Lifecycle actions have incomplete state guarantees.** Run cancellation has no pending/error feedback, and duplicate/pause/archive actions depend on eventual subscription updates instead of explicit mutation state.

13. **Frontend environment boundaries are unclear.** The local frontend environment file contains backend-only variable names. They are not browser-exposed without `NEXT_PUBLIC_`, but backend secrets and service configuration should never live in the frontend environment file.

14. **There are no automated tests.** ESLint, TypeScript, and production build pass, but `package.json` has no test script. Chat switching, onboarding recovery, routing, adapters, and mutations are currently protected only by manual testing.

15. **Documentation and deployment guidance were stale.** The README was the default create-next-app text. The TRD listed Next.js 14+, undecided styling, and `next export`, while the project uses Next.js 16, global CSS/Tailwind 4, dynamic routes, and a normal Next runtime build.

### Low priority / cleanup

16. **Legacy assets and styles remain.** `bridge.png`, `image1.png`, and the default Next/Vercel SVGs are unused. Global CSS still contains selectors for removed dashboard panels/settings rows. `recharts` is installed but unused. `frontend/docs/agents.md` is empty and duplicates the purpose implied by the real frontend rules file.

17. **The global stylesheet is becoming a feature monolith.** It is workable at the current size, but unrelated landing, auth, onboarding, dashboard, chat, settings, and run styles share one file and retain stale selectors.

18. **Modal accessibility is incomplete.** Agent settings visually behave as a modal but do not manage initial focus, focus trapping, Escape dismissal, or focus restoration.

## 3. Classification

### KEEP

- The exact current dashboard layout, styling, roster rail, chat canvas, navigation, and interaction design.
- App Router route composition and the `/chat` → `/dashboard` compatibility redirect.
- Firebase Auth context and normalized authentication errors.
- Route guards and reusable loading/error/retry state.
- Typed service boundary and the rule that mutations go through the backend API.
- Read-only Firestore listeners for realtime server state, after they are split by feature.
- Local preview adapter as an explicit development tool, not an implicit production fallback.
- Stable technical `agentId`/`runId` attribution across messages, runs, artifacts, and decisions.
- Existing create/edit/pause/archive foundations and all dashboard CSS used by the approved interface.

### CHANGE LATER

- Split monolithic types, dashboard subscriptions, and duplicated data converters by feature without reorganizing current dashboard markup or live styles.
- Make selected agent and conversation explicit URL/server state.
- Replace hardcoded template and capability lists with shared catalog/config data.
- Make onboarding atomic and draft-safe.
- Add focused server-state caching/invalidation; do not add a large global store until interaction state requires it.
- Strengthen service and mutation correctness behind the current controls without adding new dashboard UI.
- Decide and document a deployment target that supports the current Next runtime.

### REMOVE LATER

- Unused starter SVGs, unused background images, stale CSS selectors, and `recharts` if no retained visualization needs it.
- Placeholder remote conversation creation and client-only recipient mutation.
- Broad `useDashboardData` use on routes that need only one resource.
- Duplicate profile/agent decoding and duplicate template/capability constants.
- Backend-only variables from the frontend environment file.
- Empty `frontend/docs/agents.md` after confirming no external link depends on it.
- Local simulator code from production bundles once a real adapter is available; keep it in a development-only boundary if still useful.

### MISSING

- Dedicated agent summary/detail models and a schema for the fields already present: name, role, template, objective, instructions, tone, permissions, context, status, and lifecycle.
- Per-agent conversation identity and isolated one-to-one history.
- A canonical selected-agent state shared by roster, URL, chat, settings, and deep links.
- Atomic workspace + first-agent onboarding and resume/recovery behavior.
- Runtime validation/versioning for API and Firestore payloads.
- Focused data repositories/subscriptions with resource-level errors and invalidation.
- Automated unit/component/integration tests and a small end-to-end critical path.
- Robust mutation feedback and optimistic-state reconciliation.
- Explicit empty/loading/offline/error states for each major agent surface.

## 4. Incremental implementation plan

1. **Repair repository and configuration hygiene.** Unignore and commit required frontend libraries and a safe environment template; separate frontend/public values from backend secrets; make remote/local mode explicit and validated.
2. **Define the agent contracts.** Keep stable `agentId` values, add dedicated agent summary/detail models, split create/update inputs, validate the fields already present in the UI, and add runtime payload validation.
3. **Unify the data layer.** Introduce feature-scoped repositories/hooks for profile, roster, agent detail, conversations, messages, runs, and integrations; remove broad subscriptions and duplicate converters; define invalidation after mutations.
4. **Make onboarding atomic and recoverable.** Persist the draft, source templates from one catalog, allow complete first-agent customization, and mark onboarding complete only when workspace defaults and the first agent both exist.
5. **Make chat agent-safe.** Implement list/create/select conversation APIs, key one-to-one threads by agent, load history on switch, synchronize selection with the URL, isolate pending/error state per thread, and prevent cross-agent message leakage.
6. **Connect the existing dashboard without changing it visually.** Keep its render structure and styles; replace only the underlying mock/placeholder state with validated hooks and backend services.
7. **Complete existing agent management behavior.** Share template defaults, wire the current fields and lifecycle controls to backend mutations, and avoid new form sections or dashboard elements.
8. **Remove verified legacy code.** Delete unused assets/styles/dependencies and placeholder adapters only after coverage confirms no retained dashboard behavior depends on them.
9. **Add validation and rollout protection.** Cover DTO validation, onboarding recovery, agent switching, conversation isolation, create/edit/archive, auth guards, and remote/local mode; add before/after screenshots to prevent dashboard visual drift.

## 5. Validation performed during review

- `npm run lint` — passed.
- `tsc --noEmit --incremental false` — passed.
- `npm run build` — passed; all 11 current routes compiled.
- `git status --short` — clean before documentation changes.
- No application/source file was edited.

## 6. Decisions requiring product/backend alignment

- Whether any customization field beyond the current form is required. Recommended: **no** until the existing UI is fully connected and validated.
