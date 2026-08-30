# Task 3: Agent-isolated chat integration

## Objective

Complete F10 and F11 using the existing dashboard rail and chat canvas.

## Work

- Keep selected `agentId` and `conversationId` as canonical, deep-linkable route state.
- Use one-to-one conversation list/create/select operations for the selected agent.
- Scope message loading, optimistic sends, pending responses, retry, errors, and auto-scroll to that conversation.
- Verify that switching the roster always loads separate history and never mutates a prior thread’s recipient.
- Support the same isolated thread across web and Telegram once the backend persists agent and conversation attribution.
- Do not add group controls, chat surfaces, dashboard panels, indicators, or styling changes.

## Acceptance criteria

- Each message, conversation, run, and response has the selected `agentId` and correct `conversationId`.
- Browser navigation and direct `/dashboard?agent=…` links restore the correct agent and thread.
- Remote mode fails clearly until the required backend conversation contract is deployed; it never falls back to global history.

## Dependencies

- Backend agent-addressed conversation and chat endpoints.
