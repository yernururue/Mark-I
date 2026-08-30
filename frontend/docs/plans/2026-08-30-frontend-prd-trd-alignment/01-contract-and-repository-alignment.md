# Task 1: Contract and repository alignment

## Objective

Make the frontend’s data boundary conform to TRD 3.3 before connecting more controls to remote services.

## Work

- Inventory the deployed backend routes and compare them with every frontend service call.
- Define resource-specific repository interfaces for profile, agents, conversations, messages, runs, artifacts, handoffs, and integrations.
- Add runtime decoders and command serializers for all API and Firestore DTOs, following the existing agent decoder pattern.
- Keep local and remote adapters behind the same contracts; local storage remains development-only and explicitly selected.
- Move all remaining broad or duplicate loaders to focused hooks without altering page markup or dashboard styles.
- Document unsupported remote capabilities as explicit backend dependencies rather than supplying placeholder data.

## Acceptance criteria

- Invalid API or Firestore payloads cannot enter UI domain state silently.
- No route loads unrelated resources merely to render the existing roster, chat, or run screen.
- Production cannot silently select local preview data.
- Contract mismatches produce an actionable unavailable/error state.

## Dependencies

- Backend route inventory and API owner confirmation for the contracts listed in `plan.md`.

## Implementation record

- Added resource-specific repository interfaces for profile, agents, conversations, messages, runs, artifacts, handoffs, and integrations.
- Added runtime decoding for local storage, REST responses, and Firestore DTOs, plus validated command serializers for every current mutation boundary.
- Moved agent, run, artifact, and handoff remote reads to focused Firestore repositories; remote writes remain authenticated API-only.
- Removed the legacy global chat response mapping and replaced unsupported remote capabilities with actionable `backend-contract` errors.
- Made local preview an explicit development selection and made production Firebase configuration fail fast when the API base URL is missing.
- Preserved dashboard markup and styles. Run details now combine the existing roster hook with a focused run/artifact hook instead of loading a duplicate roster inside run state.
- Published the route comparison, exact required DTOs, and backend blockers in `backend-contract-gaps.md`.

## Validation

- `npm run lint` — passed.
- `npm exec tsc -- --noEmit` — passed.
- `NEXT_PUBLIC_DATA_MODE=firebase NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run build` — reached the known host-only Turbopack failure (`binding to a port: Operation not permitted`).
- `NEXT_PUBLIC_DATA_MODE=firebase NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run build -- --webpack` — passed; all 11 routes compiled and page generation completed.
