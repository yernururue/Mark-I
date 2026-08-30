# Stage 1 baseline and contract freeze

Date: 2026-08-29.  Canonical runtime: CPython 3.11, matching `Dockerfile`.

## Dependency gate

A clean CPython 3.11.15 virtual environment resolved and installed
`requirements-dev.txt` successfully; `pip check` reported no broken requirements.
The resulting exact runtime set is committed as `requirements-py311.lock` and is
the only dependency input used by the Docker build.  Notable versions are
FastAPI 0.141.1, Pydantic 2.13.5, Pydantic Settings 2.15.0, Firebase Admin
7.5.0, Firestore 2.29.0, Google ADK 2.8.0, and google-genai 2.20.0.

The unmodified suite did not collect under that environment: three collection
errors exposed the existing import/runtime failures and Pydantic emitted fourteen
deprecated `Field(env=...)` warnings.  This is the intended pre-remediation
baseline, not a successful quality gate.  Docker daemon access was unavailable;
container verification remains reserved for phase 1.6.

## Contract freeze

Generated OpenAPI remains frozen: phase 1 must not modify `openapi.yaml` or
public API schemas.  Import-only smoke tests must never start external services;
startup/lifespan tests own explicit startup validation.  Tests use only
test-defined values and must not read developer `.env` files or ADC.

## Defect matrix

| Defect | Owning phase | Regression gate | Exit criterion |
| --- | --- | --- | --- |
| Eager settings and deprecated environment metadata | 1.1 | config accessor and warning tests | lazy cached settings; zero env warnings |
| Missing FastAPI dependencies and GitHub factory typo | 1.2 | router import/OpenAPI tests | all routers import with overrides |
| `backend.*` imports and worker module globals | 1.3 | Docker-layout worker import test | canonical top-level imports, no client construction |
| Unsupported `google.antigravity` | 1.4 | AI adapter import/result tests | supported ADK adapter and validated result |
| Tuple Firestore filters and client transaction decorator | 1.5 | filter/transaction behavior tests | production SDK API only |
| Python 3.11 container integration | 1.6 | image import and `/health` smoke | Docker image passes all runtime gates |

Strict xfails for stages 2--5 (event envelope, idempotency, public schema,
deployment security, and opportunity semantics) are explicitly out of scope and
must retain their markers unless their owning stage is implemented.
