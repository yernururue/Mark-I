# Mark-I frontend

Mark-I is a Next.js workspace for **Multiple Customizable Agents**: user-created AI collaborators with separate identities, behavior, permissions, conversations, runs, and outputs.

The current dashboard is the approved product UI. Keep its layout, styling, roster, chat canvas, navigation, and interaction design visually unchanged; refactor only the internals needed for cleanup, correctness, and backend integration.

## Stack

- Next.js 16 App Router
- React 19 and strict TypeScript
- Firebase Auth
- Firestore read listeners for realtime data
- Backend REST API for mutations
- Global CSS with Tailwind 4 build processing
- Local browser adapter for development previews

## Routes

| Route | Current purpose |
|---|---|
| `/` | Landing page |
| `/login` | Firebase sign-in and sign-up |
| `/onboarding` | Workspace defaults and first-agent setup |
| `/dashboard` | Chat-first dashboard and agent switcher |
| `/chat` | Compatibility redirect to `/dashboard` |
| `/agents` | Agent management |
| `/agents/[agentId]` | Agent configuration and lifecycle |
| `/runs/[runId]` | Run timeline and outputs |
| `/settings` | Workspace defaults and integrations |
| `/auth/github/callback` | GitHub OAuth completion |

**Agent** is the single product and technical term across the frontend, backend, Firestore, and runtime. `agentId` remains the stable identifier.

## Local development

```bash
npm install
npm run dev
```

Useful validation commands:

```bash
npm run lint
npx tsc --noEmit --incremental false
npm run build
```

There is currently no automated test command.

## Browser-safe configuration

Only browser-safe variables belong in the frontend environment:

```text
NEXT_PUBLIC_FIREBASE_API_KEY
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
NEXT_PUBLIC_FIREBASE_PROJECT_ID
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID
NEXT_PUBLIC_FIREBASE_APP_ID
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_DATA_MODE
NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
```

Do not place GitHub secrets, Telegram bot tokens, service-account paths, Pub/Sub configuration, or other backend secrets in `frontend/.env.local`.

`NEXT_PUBLIC_DATA_MODE` accepts `local` or `firebase`. Local mode must be selected explicitly, uses validated `localStorage` data and simulators, and is rejected by production builds. Firebase is the non-local default; production Firebase builds also require `NEXT_PUBLIC_API_URL`.

## Architecture

- `app/` — route composition
- `components/` — shared and feature UI
- `contexts/` — Firebase authentication state
- `hooks/` — current feature state and subscriptions
- `services/` — resource repository contracts, typed operations, and explicit data-source selection
- `services/adapters/` — local development persistence
- `types/` — current shared models
- `lib/` — runtime DTO decoders, command serializers, API, Firebase, configuration, error, and ID utilities
- `docs/` — frontend plans and reviews

External REST, Firestore, and local-preview payloads remain `unknown` until a resource decoder accepts them. Unsupported remote capabilities return actionable backend-contract errors and never fabricate production data.

## Review and plan

See [the Multiple Customizable Agents frontend review](docs/2026-08-29-multiple-agents-frontend-review.md) and the active [PRD/TRD alignment plan](docs/plans/2026-08-30-frontend-prd-trd-alignment/plan.md).
