# Task 08 — Chat, opportunities and deployment

## Findings

R-03, X-01, X-03, X-04 and residual end-to-end risks exposed by the Stage 1–3 review.

## Changes

- Add a client/request turn id and durable turn state shared by web and Telegram. Serialize or transactionally order turns per user so replies cannot attach to the wrong prompt.
- Reuse deterministic message IDs and stable history ordering across both channels; retries return the original completed turn.
- Bound agent tool iterations and expose the chat model/tool runner behind the same credential-free adapter seam.
- Authenticate the opportunity trigger fail-closed (Cloud Run IAM/OIDC or an equally explicit verified scheduler identity).
- Separate opportunity persistence from Telegram delivery: unlinked users still receive deduplicated opportunity/decision data, with delivery marked `suppressed` rather than skipping the business record.
- Apply threshold semantics once per `opportunity + uid` and make repeated scheduler/Pub/Sub delivery idempotent.
- Update Cloud Build/Run configuration with every required non-secret environment setting and Secret Manager binding; keep secrets out of source, images and logs.

## Acceptance

- Concurrent web and Telegram turns preserve deterministic prompt/reply pairing and unified cursor order.
- Duplicate turn IDs and Telegram updates do not invoke AI twice.
- Tool loops stop at a configured bound with a recorded terminal error.
- All four existing strict xfails pass as ordinary tests and are removed only with their implementation.
- Unauthenticated triggers fail; authenticated scheduler requests succeed.
- Linked and unlinked users both persist one opportunity decision, while only eligible linked users get one delivery.
- Built container receives validated role configuration through deployment manifests without exposing secret values.

## Dependencies

Tasks 05, 06 and 07.

