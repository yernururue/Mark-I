# Task 03 — GitHub event extractors

## Objective

Replace the push/PR-only string builder with a registry of explicit extractors for all webhook events registered by `select_repos()`.

## Canonical context

Define a validated `GitHubEventContext` with `repo`, `eventType`, optional `ref`, optional `title`, optional `description`, required meaningful `changesText`, and JSON-safe `metadata`. Every context metadata payload includes delivery ID, repository, event type, source reference/URL when GitHub supplied one, and relevant action fields.

## Scope after approval

1. Create `EVENT_EXTRACTORS` for `push`, `pull_request`, `pull_request_review`, `issues`, `issue_comment`, and `create`.
2. Implement payload-safe extractor functions with well-defined optional-field handling:
   - **push:** ref, commits, messages and file-change summaries;
   - **pull_request:** action, title/body, branch/ref, URL and merge state;
   - **pull_request_review:** review body/state plus pull-request title/URL;
   - **issues:** action, title/body, labels and URL;
   - **issue_comment:** comment body/action plus issue or pull-request context and URL;
   - **create:** ref type, ref name and repository context.
3. Route the typed context to the Stage-1 analyzer without changing its validated analysis-result contract.
4. Explicitly recognize an unknown event type, write sanitized structured diagnostics, and let task 02 ACK it without an AI call, observation, skill update, decision or notification.
5. Bound context size at the extractor/analyzer boundary using the existing Stage-1 safe-input policy; never log complete source payloads.

## Files expected to change after approval

- a focused worker/domain extractor module and its models;
- `workers/github_worker.py` orchestration;
- AI request adapter only if its already-approved typed boundary needs the context;
- focused extractor and worker tests.

## Tests and acceptance

Use representative minimal and rich fixtures for all six event types. Assert populated `changesText`, correct action/ref/title metadata, absence-tolerant optional fields, and preserved delivery correlation. Assert unknown event has no analyzer or business-service call. All six subscriber event names must map to one extractor; no supported type may produce an empty prompt.

## Rollback boundary

The context model, registry, six extractors and tests are one rollback unit. Keep the legacy `get_changes_text` implementation only until this unit is fully migrated, then remove it in the same commit.
