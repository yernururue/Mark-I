# Frontend Agent Rules

## Responsibility Area

This is the **frontend agent's** responsibility area. The frontend agent owns all files under `frontend/`.

---

## Ownership Boundaries

### You Own

- `frontend/` — all implementation files and subdirectories
- `frontend/agents.md` — this file (frontend agent rules)
- `frontend/TRACKER.yaml` — frontend task tracker
- `frontend/docs/` — frontend-specific documentation and plans

### You Must NOT Modify

- `backend/` — backend implementation (requires **explicit user permission**)
- `backend/agents.md` — backend agent rules
- `backend/TRACKER.yaml` — backend task tracker

### Shared Resources (Modify Only When Required)

- `docs/prd.md` — Product Requirements Document
- `docs/trd.md` — Technical Requirements Document
- `docs/TRACKER.yaml` — Global project tracker (update when major milestones are completed)

---

## Session Start Checklist (MANDATORY)

At the start of every implementation session:

1. Read `frontend/TRACKER.yaml` to understand current progress
2. Read `docs/prd.md` and `docs/trd.md` to understand project requirements
3. Resume work from where the last session left off
4. Do **not** begin new work without checking the tracker first

---

## Planning Workflow

All frontend plans live in `frontend/docs/plans/`.

### Creating a Plan

1. Create `frontend/docs/plans/YYYY-MM-DD-feature-name/` with:
   - `plan.md` — overview, goals, architecture, scope
   - `diagram.excalidraw` — architecture diagram
   - `blockers.excalidraw` — dependency/blocker diagram
   - Numbered task files (`01-task-name.md`, `02-task-name.md`, etc.)

2. Register the plan in `frontend/TRACKER.yaml`

### Plan Requirements

Every plan **MUST** contain:
- `plan.md`
- `diagram.excalidraw`
- `blockers.excalidraw`
- At least one numbered task file

**NEVER** create a plan without all required files.

---

## Task Lifecycle

Tasks: `pending` → `in-progress` → `done`
Plans: `planned` → `in-progress` → `shipped`

### When starting a task:
- Update `frontend/TRACKER.yaml` — task status to `in-progress`
- If first active task, set parent plan to `in-progress`

### When completing a task:
- Update `frontend/TRACKER.yaml` — task status to `done`
- Identify newly unblocked tasks

### When blocked:
- Leave status as `in-progress`
- **Report the blocker explicitly** — do NOT silently skip

### When all tasks complete:
- Compile `README.md` from plan and task files
- Move to `frontend/docs/systems/<system-name>/`
- Set plan status to `shipped` in `frontend/TRACKER.yaml`
- Update `docs/TRACKER.yaml` with the milestone

---

## Global Tracker Synchronization

When a major frontend milestone is completed:
- Update `frontend/TRACKER.yaml` (detailed)
- Update `docs/TRACKER.yaml` (high-level summary)

The global tracker must **never** contradict the frontend tracker.

---

## Key Rules

| Rule | Description |
|------|-------------|
| **Stay in your area** | Only modify files under `frontend/` |
| **Cross-area changes** | Require explicit user permission |
| **Check tracker first** | Always inspect `frontend/TRACKER.yaml` before starting work |
| **Respect PRD/TRD** | Read and follow `docs/prd.md` and `docs/trd.md` |
| **No silent skips** | Report blockers explicitly |
| **Keep tracker in sync** | Update on every state change |
