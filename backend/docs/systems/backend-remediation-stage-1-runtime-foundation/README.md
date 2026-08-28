# Backend remediation stage 1 — runtime foundation

Completed 2026-08-29.

## Delivered

- Reproducible CPython 3.11 dependency lock used by the Docker image.
- Lazy, typed settings lifecycle with role-aware, sanitised validation.
- FastAPI dependency providers for verified authentication, Firestore, and services.
- Docker-compatible package layout and worker composition roots without import-time GCP clients.
- Google ADK GitHub analyzer with validated proficiency and significance fields.
- Production-shaped Firestore `FieldFilter` and transactional skill updates.
- Container proof for API/workers import and `/health`.

## Verification

- Clean Python 3.11 install: `pip check` passed.
- Full backend suite: 80 passed, 18 expected xfailed, 0 failed.
- Docker image `mark-i-stage1:local` built successfully.
- `app.main`, `workers.github_worker`, and `workers.opportunity_worker` imported in image.
- `/health` returned HTTP 200 using TestClient and a running Docker container.

The remaining xfails are explicitly owned by remediation stages 2--5 and were not changed.
