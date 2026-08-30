# Task 06 — Canonical API, errors and profile

## Findings

F-06, F-10, F-13, R-02 (DI portion).

## Changes

- Expand contract parity from top-level field names to paths, methods, operation security, parameters, required fields, enums, bounds, formats, nullable/default semantics and recursive response/error schemas.
- Align FastAPI/Pydantic with canonical `openapi.yaml`, including Firebase bearer security, protected-route 401 responses, GitHub header enum, Chat/Observation/Skill constraints and the intended Dashboard skill shape.
- Register the common JSON error envelope for FastAPI and Starlette HTTP exceptions, validation errors and uncaught server errors while preserving correct status/header semantics.
- Make profile create a Firestore create/precondition or transaction so concurrent POSTs cannot overwrite an existing user.
- Strip then validate `displayName` and free-form `goal` (`1..500`); keep skills out of profile writes and responses.
- Route every endpoint through canonical FastAPI dependencies/service factories so test overrides work uniformly.

## Acceptance

- A deep generated-vs-canonical OpenAPI test reports no semantic differences in the supported contract surface.
- Authenticated routes advertise security and documented 401/error responses.
- Framework 404, 405, request validation, domain errors and unexpected errors all use the common envelope.
- Concurrent profile creates return one 201 and one conflict without data overwrite.
- Whitespace-only display name/goal fails; trimmed valid values persist; profile never duplicates `skills`.

## Dependencies

Task 01.

