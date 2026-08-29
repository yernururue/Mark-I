# Task 5: Validation and handoff

- Add focused unit/component/integration tests for DTO validation, onboarding recovery, agent creation/editing, selection, conversation isolation, retries, archive, and adapter parity.
- Add a small end-to-end critical path: sign in → onboard → create second agent → switch threads → send messages → edit/archive.
- Run lint, TypeScript, and production build checks.
- Compare before/after dashboard screenshots and reject unintended visual or layout changes.
- Verify explicit local and remote configurations and confirm no backend secret is used by the frontend build.
- Remove only assets, selectors, dependencies, duplicate loaders, and placeholder adapters proven unused after coverage is in place.
- Keep `/agents` routes canonical and document rollback boundaries for the refactor.
- Keep the frontend README, PRD, TRD, review, and trackers consistent.
- Reconcile area/global trackers and ship the plan when all tasks are complete.
