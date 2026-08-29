# 01 — Canonical OpenAPI and error envelope

Use `openapi.yaml` as the compatibility policy. Add contract tests for generated FastAPI OpenAPI and normalize validation, HTTP and domain failures to the documented `{"error": {"code", "message"}}` envelope.

## Done when

- The parity test checks paths, methods, required request fields and response body shapes.
- Error handlers cover request validation, HTTP/domain errors and unexpected exceptions.
- API docs describe the same error envelope and free-form goal constraints.

