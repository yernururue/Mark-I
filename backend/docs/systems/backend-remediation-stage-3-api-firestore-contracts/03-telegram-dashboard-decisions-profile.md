# 03 — Telegram, dashboard, decisions and profile

Bring Telegram linking, decision documents, dashboard aggregation and profile validation to their published contracts. Keep Firestore access in services.

## Done when

- Link response contains `linkCode`, `expiresAt`, `botUsername`; code consumption is transactional and single-use.
- Telegram user and chat IDs are stored separately; unlink is idempotent and service-owned.
- Dashboard is built from stored skills, observations and decisions; decisions contain action, threshold and intensity.
- Goals are free text constrained to 1..500 and profiles do not duplicate `/skills`.

