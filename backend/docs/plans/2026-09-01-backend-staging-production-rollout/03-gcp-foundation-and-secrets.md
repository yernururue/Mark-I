# 03 — GCP foundation and secrets

## Objective

Create the minimum identities, permissions, registry, secrets, and indexes needed for deployment.

## Tasks

- Create or verify the Artifact Registry repository and five dedicated service accounts.
- Present exact IAM targets and obtain confirmation before applying grants.
- Grant build, runtime, secret, Pub/Sub, Vertex AI, Firestore, and Cloud Run permissions at the narrowest practical scope.
- Create or verify the six named Secret Manager resources without printing secret values.
- Add secret versions from protected inputs or in-memory generated values.
- Create every composite index declared in `backend/firestore.indexes.json` and wait for `READY`.

## Exit criteria

- Required resources exist, indexes are ready, and IAM inspection shows no unintended principals.
- Secret payloads have never appeared in console output, files, or logs.
