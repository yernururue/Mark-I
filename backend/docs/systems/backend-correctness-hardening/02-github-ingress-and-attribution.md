# Task 02 — GitHub ingress and actor attribution

## Findings

F-02.

## Changes

- Define one physical Mark-I webhook per repository endpoint and a separate set of user subscriptions, instead of registering one indistinguishable hook per user.
- Add reconciliation for existing duplicate hooks without deleting unrelated third-party hooks.
- Validate HMAC over the exact request bytes with constant-time comparison before parsing or publishing.
- Accept only the documented GitHub event/action matrix; unsupported events return a successful ignored result and create no Pub/Sub message.
- Derive a canonical actor for every supported event (`sender`, `pusher`, PR author/reviewer as appropriate), then fan out only to connected users whose GitHub identity matches that actor under the documented policy.
- Preserve `deliveryId` for transport audit, derive a stable `activityId`, and use `activityId + uid` as the logical business key. Include envelope version, event/action, repository identity and actor identity.
- Add multi-user fixtures for a shared repository, duplicate physical hooks, bot actors and missing actor mappings.

## Acceptance

- Two users subscribed to one repository produce exactly one effect for the user who performed the activity.
- Two deliveries caused by legacy duplicate hooks do not multiply business effects.
- HMAC failure, unsupported type/action and malformed payload produce no publish.
- Every supported event serializes and deserializes through the versioned envelope.

## Dependencies

Task 01 for runtime-safe factories.
