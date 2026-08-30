# Task 03 — GitHub evidence and assessment

## Findings

F-07 and the extractor/proficiency correctness part of F-02.

## Changes

- Keep event extractors deterministic and typed; they produce metadata and references, never proficiency scores.
- Fetch bounded code evidence for code-bearing events through an injectable GitHub client: commit patches for push and changed-file patches/diff for pull requests and reviews.
- Apply file-count, byte, binary/generated/vendor and secret-redaction limits; record truncation explicitly.
- Do not infer code proficiency from titles, commit messages or filenames alone. Events without usable evidence may yield significance but no proficiency mutation.
- Keep proficiency assessment and significance as distinct analyzer fields and distinct policy inputs.
- Validate the complete analysis before persistence; a blank concept or invalid assessment creates no partial observation.
- Document rate-limit and retry classification for evidence retrieval.

## Acceptance

- Tests prove patches, not only prose metadata, reach the proficiency analyzer.
- Non-code issue/comment/create events cannot change proficiency unless the product policy explicitly supplies assessable evidence.
- Binary-only, oversized, redacted, unavailable and rate-limited evidence have deterministic outcomes.
- Malformed analysis causes zero observation/skill/decision writes.

## Dependencies

Tasks 01 and 02.

