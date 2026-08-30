# 02 — Chat and observations contracts

Align chat request/response fields and move history retrieval into `ChatService`. Implement deterministic cursor pagination and source/concept filtering for observations.

## Done when

- Chat accepts `message` and required `channel`, validates 1..2000 characters, and returns persisted IDs.
- Chat history exposes `messages`, `nextCursor` and `hasMore` with channel filtering.
- Observation pages expose `observations`, `nextCursor` and `hasMore`; filters and next pages do not leak or duplicate data.

