# Task 05 — Telegram identity, updates and delivery

## Findings

F-04 (destination portion), F-05, F-09, R-05, X-02.

## Changes

- Add a unique `telegram_identities/{telegramUserId}` ownership record claimed transactionally with the user link; reject attempts to bind the same Telegram identity to another Mark-I account.
- Use `message.from.id` only for identity and `chat.id` only for destination. Require private chats for linking, AI chat and private notifications; group/supergroup requests receive a safe refusal without profile disclosure.
- Generate link codes with `secrets`, store a hash rather than a reusable plaintext secret, create them transactionally without collision overwrite, and consume exactly once with expiry.
- Keep unlink idempotent while atomically releasing the identity mapping only when it still belongs to the caller.
- Deduplicate Telegram webhook updates by `update_id` with claim/lease/retry state before invoking chat or sending a reply.
- Make webhook-secret verification mandatory outside an explicit local-test role and compare it in constant time.
- Route GitHub/opportunity notifications to persisted `telegramChatId`, never `telegramUserId`.
- Send AI/user content as plain text or correctly escaped markup and check the send result; persist reply/delivery state consistently with unified history.

## Acceptance

- Concurrent link attempts for one code or one Telegram identity produce one owner and no split records.
- Same-code replay, collision, expiry and idempotent unlink tests pass.
- Group-chat updates cannot link, query or expose a user's Mark-I profile.
- Repeated `update_id` invokes the AI and creates/sends each message at most once.
- Missing/incorrect webhook secret fails closed; local tests opt into bypass explicitly.
- Notification tests assert the private chat destination and every delivery status transition.

## Dependencies

Task 04 for the delivery state machine.

