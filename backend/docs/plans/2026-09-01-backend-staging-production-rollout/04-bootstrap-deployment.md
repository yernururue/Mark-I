# 04 — Bootstrap Cloud Build deployment

## Objective

Deploy production-named services while keeping recurring production traffic disabled.

## Tasks

- Present the exact build, services, region, image repository, substitutions, and Telegram webhook target for confirmation.
- Submit `backend/cloudbuild.yaml` with an immutable tag and sanitized substitutions.
- Wait for build completion and inspect step status without exposing secret values.
- Verify healthy revisions for `mark-i-api`, `mark-i-github-worker`, and `mark-i-opportunity-worker`.
- Confirm API public access, worker private access, runtime identities, environment, and secret bindings.
- Compare the actual API URL with the predicted URL and repair URL-dependent configuration if needed.

## Exit criteria

- Build succeeds and all services pass health/readiness checks.
- No scheduler exists and existing pull subscriptions have not yet been switched.
