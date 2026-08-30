# Task 01 — Runtime and AI contract

## Findings

F-01, F-07 (schema portion), R-02 (runtime portion).

## Changes

- Replace the unsupported plain-string ADK invocation with the SDK's typed user `Content`/`Part` input behind an injectable analyzer adapter.
- Keep production model/session/runner construction lazy. Tests inject a fake adapter and never resolve ADC, Gemini or other real credentials.
- Make analyzer output strict: non-blank normalized concept, bounded proficiency assessment, significance kept separate, and explicit retryable versus terminal errors.
- Treat malformed or semantically empty model output as an atomic failure before any observation, skill or decision write.
- Constrain `ENV` to known values and validate required settings by executable role, including Telegram webhook/bot requirements where relevant.
- Preserve Python 3.11 and Docker top-level package imports; no import-time Firestore, Pub/Sub, Secret Manager, Firebase, GitHub or ADK clients.

## Acceptance

- A real installed ADK runner boundary accepts the produced typed message in a no-network seam test.
- Analyzer tests cover valid output, blank concept, invalid proficiency, malformed JSON, timeout and provider failure.
- Import probes for app and every worker pass with credential variables absent.
- Settings reject unknown environments and missing role-specific configuration before serving traffic.
- Existing dependency overrides remain possible without patching module globals.

## Dependencies

None.

