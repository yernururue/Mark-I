# Task 2: Authentication and onboarding

- Normalize provider and email authentication errors and submission states.
- Route users based on persisted onboarding completion, not provider metadata.
- Preserve onboarding drafts and support safe resume after refresh, auth interruption, or a failed request.
- Source templates and capabilities from the same catalog used by later agent creation.
- Submit the current workspace-default and first-agent form fields without expanding or visually redesigning onboarding.
- Finalize onboarding only after both workspace defaults and the first agent exist; use one backend transaction/command where possible.
- Make retries idempotent and define recovery for a profile that exists without an agent.
