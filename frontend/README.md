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

`NEXT_PUBLIC_DATA_MODE` currently accepts `local` or `firebase`. Local mode uses `localStorage` and simulated responses; Firebase mode uses Firebase Auth/Firestore reads plus the REST API for mutations.

## Architecture

- `app/` — route composition
- `components/` — shared and feature UI
- `contexts/` — Firebase authentication state
- `hooks/` — current feature state and subscriptions
- `services/` — typed operations and data-source selection
- `services/adapters/` — local development persistence
- `types/` — current shared models
- `lib/` — API, Firebase, configuration, error, and ID utilities
- `docs/` — frontend plans and reviews

The target refactor will keep these concepts while splitting server state by feature, validating agent DTOs at data boundaries, and isolating each agent conversation.

## Review and plan

See [the Multiple Customizable Agents frontend review](docs/2026-08-29-multiple-agents-frontend-review.md) and the active [frontend product-readiness plan](docs/plans/2026-08-29-frontend-product-readiness/plan.md).
