# Frontend product-readiness plan

## Goal

Turn the existing static frontend into the coherent Mark-I configurable multi-agent workspace defined by the PRD and TRD, without coupling UI components to Firebase or unfinished backend endpoints. Developer mentoring remains the first template, not a separate product path.

## Audit summary

- Authentication providers are wired directly inside a modal and routing is based on Firebase metadata rather than persisted onboarding state.
- Onboarding creates an underspecified agent with a direct Firestore write instead of collecting workspace defaults and a complete first-agent configuration.
- Dashboard data types, Firestore listeners, loading state, and errors are combined in one hook; the hook reports loading complete before subscriptions resolve.
- Dashboard navigation, search, settings, and chat are incomplete or inert. Chat has no message history, send action, pending/error state, retry, or backend abstraction.
- Profile, settings, Telegram linking, GitHub connection, onboarding submission, and chat mutations lack typed services.
- Pages duplicate authentication redirects and render blank/loading-only screens without a reusable route guard.
- Several UI controls are non-semantic or inaccessible, the mobile dashboard is unusable, and lint currently fails.
- Frontend-local environment configuration contains backend-only variable names. The frontend must document only browser-safe Firebase values and the public API URL.

## Target architecture

- `types/` owns stable domain and API-facing models.
- `services/` owns typed auth, user/onboarding, agents, runs, artifacts, dashboard, integrations, and multi-agent chat contracts.
- `lib/firebase/` owns Firebase initialization and read-only Firestore adapters.
- `features/` owns product-specific hooks and stateful UI.
- `components/` owns reusable presentational and route-state components.
- `app/` owns route composition and navigation only.

The default development adapter may use local browser persistence when the backend is unavailable. Replacing it with real REST endpoints must not require rewriting route or UI components.

## Product flow

Authentication → onboarding status check → workspace defaults and first agent → dashboard → agent roster → individual agent / run / chat flows → settings and integrations.

## Constraints

- Preserve the existing dark, restrained visual language and existing dependencies.
- Firebase Auth remains client-side; Firestore is read-only from the browser.
- All mutations go through services, even when a local adapter supplies the current implementation.
- Do not invent backend-only business logic or secrets.
- Keep TypeScript strict and avoid `any`.

## Validation

- ESLint
- TypeScript no-emit check
- Next.js production build
- Manual browser inspection of authentication gating, onboarding, dashboard, chat send/retry behavior, settings, navigation, empty states, and responsive layout
