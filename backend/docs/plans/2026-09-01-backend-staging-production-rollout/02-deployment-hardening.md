# 02 — Deployment hardening

## Objective

Make the backend deployment deterministic and secret-safe before it touches GCP runtime resources.

## Tasks

- Move the Cloud Build image target from implicit Container Registry to the regional Artifact Registry repository.
- Add an explicit immutable image tag input suitable for manual builds.
- Bind dedicated runtime service accounts and the required Vertex AI environment.
- Wire all required substitutions and production frontend origin.
- Preserve private worker ingress and authenticated push configuration.
- Sanitize Telegram error logging so URLs, exception text, and response bodies cannot expose bot credentials.
- Run focused and full backend tests without changing tests or xfails.

## Exit criteria

- Cloud Build configuration is internally complete and inspectable.
- Backend tests pass and `frontend/` remains untouched.
