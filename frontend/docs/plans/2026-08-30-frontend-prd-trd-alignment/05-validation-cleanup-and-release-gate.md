# Task 5: Validation, cleanup, and release gate

## Objective

Prove PRD/TRD compliance and dashboard preservation before frontend release.

## Work

- Add a lightweight test runner and focused unit tests for DTO decoding, command serialization, template defaults, and local adapter behavior.
- Add component/integration tests for onboarding recovery, agent lifecycle actions, URL selection, conversation isolation, retry, and route guards.
- Capture approved dashboard screenshots before and after integration changes at supported viewport sizes; reject visual drift.
- Run lint, strict TypeScript, local-mode build, remote-mode build, and critical-path browser verification.
- Remove `recharts`, starter assets, stale selectors, duplicate loaders, and placeholder adapters only after tests and import checks prove they are unused.
- Document environment separation and the Turbopack host limitation with the verified webpack fallback.

## Acceptance criteria

- Validation covers the required PRD journeys from sign-in through agent switch, message send, lifecycle action, and run inspection.
- The dashboard screenshot comparison shows no layout or styling change.
- Production configuration uses browser-safe variables only.
- Every cleanup deletion is backed by passing tests, import checks, and a successful build.
