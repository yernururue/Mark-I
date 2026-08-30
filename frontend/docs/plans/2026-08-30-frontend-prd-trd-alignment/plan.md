# Frontend PRD/TRD alignment plan

## Goal

Complete the remaining frontend work required by the PRD and TRD for Multiple Customizable Agents. This plan starts from commit `b7b1316`: it preserves the approved dashboard exactly while completing data integrity, backend-contract integration, onboarding, agent management, and validation.

## Scope

### In

- PRD features F1–F4 and F10–F19 where the frontend is responsible.
- TRD sections 3.2–3.6: routes, data boundaries, client-side state, Firestore reads, API mutations, and configuration.
- Existing routes and components only; internal service, hook, type, and test changes are expected.
- Explicit contract handoff for backend capabilities that the frontend cannot supply.

### Out

- Any dashboard redesign, restyling, layout change, new panel, new widget, badge, indicator, or navigation pattern.
- Backend implementation, Firestore writes, agent execution, policy decisions, webhooks, secret storage, and deployment changes.
- Group-chat UI, team workspaces, billing, marketplace, or native mobile work.

## Audit baseline

| Area | Current state | Plan action |
|---|---|---|
| Dashboard | Existing shell and chat interface are preserved; selection is URL-addressable. | Keep unchanged; use screenshot comparison as a release gate. |
| Agent model | Agent DTO decoding, create/update command types, and focused roster reads exist. | Extend validation to the remaining profile, run, artifact, integration, and message payloads. |
| Chat | Local mode creates a separate conversation per agent. Remote mode correctly refuses unsupported agent-specific chat. | Integrate real remote conversations after the backend contract exists. |
| Onboarding | The profile is written before the first agent; drafts and idempotent recovery do not exist. | Add draft persistence and atomic/recoverable completion. |
| Management | Existing create, edit, duplicate, pause, archive, run, and integration controls exist. | Align each mutation to validated, deployed contracts and invalidate focused resources. |
| Validation | Lint, TypeScript, and webpack production build pass; no test runner or visual regression gate exists. | Add focused tests, contract fixtures, and dashboard screenshot parity checks. |

## Required backend contract dependencies

The frontend must not fabricate these resources. Backend ownership is required before the dependent frontend task can ship.

| Capability | Required contract |
|---|---|
| Agent management | Authenticated list/get/create/update agent endpoints, stable `agentId`, lifecycle state, and timestamps. |
| One-to-one chat | Conversation list/create/select by `agentId`; messages and `POST /chat` must carry `conversationId` and `agentId`. |
| Onboarding | One idempotent command that creates/reconciles workspace defaults and the first agent, or an equivalent recoverable transaction contract. |
| Integrations | Deployed GitHub connect/callback/repository/disconnect and Telegram link/unlink endpoints matching the frontend DTOs. |
| Runs | Agent-attributed run list/detail/cancel and artifact access contracts with realtime Firestore documents. |

## Ordered implementation plan

1. Establish frontend repository interfaces and runtime decoders for every PRD/TRD resource; publish the exact backend dependency matrix without changing backend code.
2. Consolidate the existing template and capability definitions, persist onboarding drafts, and implement idempotent/recoverable first-agent setup using the approved onboarding UI.
3. Integrate agent-isolated remote conversations once the backend contract is available; retain the current chat presentation and reject any cross-agent history.
4. Align existing agent lifecycle, run, GitHub, and Telegram controls with the verified backend contracts, resource-scoped state, and mutation feedback.
5. Add unit, component, and integration coverage; validate local and remote modes, inspect the existing dashboard visually, and remove only proven-unused legacy code.

## Completion criteria

- The dashboard remains visually and structurally unchanged.
- Every frontend-owned PRD acceptance criterion has a mapped implementation and verification result.
- All external payloads are validated before entering domain state.
- Each selected agent has an isolated one-to-one thread in both local and remote modes.
- Onboarding is atomic or safely recoverable.
- Lint, TypeScript, tests, and production build pass in explicit local and remote configurations.

## Risks and blockers

- The current backend exposes a single-agent-era chat API (`text` only and global message history). It cannot satisfy F10/F16 remote behavior until it adds the contract above.
- The current local frontend environment contains backend-only variables. Do not migrate or expose them in frontend code; separate them before remote deployment.
- The default Turbopack production build is blocked by this host’s internal-port restriction. The webpack build path is the verified local fallback until the host issue is resolved.
