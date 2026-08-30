# Task 2: Atomic onboarding and shared agent catalog

## Objective

Meet F2, F15, and TRD 3.6 while preserving the current onboarding screens and fields.

## Work

- Extract the existing Mentor, Designer, Custom, tool, and context definitions into one shared catalog used by onboarding and agent management.
- Persist a versioned onboarding draft locally with clear resume, reset, and retry behavior.
- Validate each step and submit the current workspace-default and first-agent fields through a single idempotent backend command when available.
- Provide a recovery path for a profile that already exists but has no first agent.
- Keep the four current steps, their fields, and their visual treatment unchanged.

## Acceptance criteria

- Refresh, authentication interruption, and retry preserve the user’s valid draft.
- Onboarding is considered complete only when workspace defaults and a first agent both exist.
- Templates apply complete editable defaults consistently in onboarding and management.
- Duplicate submissions cannot create duplicate first agents.

## Dependencies

- Backend onboarding transaction/reconciliation contract.
