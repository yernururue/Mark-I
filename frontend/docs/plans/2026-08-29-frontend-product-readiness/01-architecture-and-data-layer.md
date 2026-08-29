# Task 1: Architecture and data layer

- Fix the root ignore rule so required `frontend/lib/` modules and a safe environment example are reproducible in fresh clones and CI.
- Keep stable `agentId` values and introduce dedicated, validated agent summary/detail models with explicit DTO mappers.
- Split create, update, summary, detail, conversation, message, and customization contracts instead of deriving writes from one domain type.
- Add runtime validation for API and Firestore payloads and version the agent customization shape.
- Replace the monolithic dashboard subscription with feature-scoped repositories and hooks.
- Consolidate duplicate roster/profile loaders and decoders behind one explicit local-or-remote adapter boundary.
- Validate configuration at startup and never silently enter local preview mode in production.
