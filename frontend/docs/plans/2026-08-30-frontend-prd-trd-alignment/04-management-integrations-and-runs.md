# Task 4: Existing management, integrations, and run controls

## Objective

Complete F3, F4, F12, F13, F16–F19 through the current management, settings, and run-detail interfaces.

## Work

- Wire existing create, edit, duplicate, pause, archive, and run-cancel actions to validated service commands and focused resource invalidation.
- Confirm stable `agentId` propagation across agent records, conversations, runs, artifacts, decisions, and handoffs.
- Align the current GitHub OAuth, repository selection, Telegram link/unlink, and status controls with deployed backend DTOs.
- Subscribe only to the Firestore resources rendered by the current route and retain the existing loading, error, and unavailable states.
- Ensure all actions handle authorization, unavailable backend capabilities, retries, and stale route selection safely.

## Acceptance criteria

- Mutating one agent cannot alter another agent’s grants, status, runs, artifacts, or conversation.
- GitHub and Telegram actions match the deployed API path, request shape, and response shape.
- Run detail displays only data attributed to its run and agent; cancellation refreshes the existing view.
- No new dashboard UI is introduced.

## Dependencies

- Backend agent, run, artifact, GitHub, Telegram, and handoff contract confirmation.
