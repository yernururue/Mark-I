# Task 3: Dashboard preservation and backend-connected chat

- Freeze the current dashboard shell, agent rail, chat canvas, layout, styling, navigation, and component arrangement.
- Do not add panels, widgets, badges, indicators, rail elements, or a replacement dashboard.
- Reuse the current loading, empty, error, retry, composer, and message states.
- Make selected agent and conversation identity canonical, URL-addressable state shared by the rail and chat surface.
- Replace the fabricated remote workspace conversation with list/create/select conversation contracts.
- Load separate one-to-one history when switching agents and prevent cross-agent history leakage.
- Preserve the working composer, optimistic messages, pending state, failures, retry, keyboard behavior, and auto-scroll while scoping them per conversation.
- Wire the existing dashboard components to validated backend services without changing their visual output.
