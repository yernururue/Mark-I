# 05 — Staging end-to-end acceptance

## Objective

Prove real staging behavior on the production-named services using bounded synthetic fixtures.

## Tasks

- Present both subscription targets and obtain confirmation before pull-to-push conversion.
- Configure authenticated push to both private worker services and verify invoker/token-creator bindings.
- Verify API `/health`, authenticated worker health, and rejection of unauthenticated worker access.
- Submit a valid-HMAC GitHub webhook and a duplicate delivery; prove a single business effect.
- Exercise Telegram link, private-chat update, duplicate update, and unlink.
- Exercise opportunity processing for one linked and one unlinked synthetic user.
- Prove acknowledged Pub/Sub delivery to each worker and inspect sanitized logs/metrics.

## Exit criteria

- Every required scenario passes with persisted, queryable evidence.
- Failed external Telegram delivery to a synthetic chat is terminal and does not block worker acknowledgement.
