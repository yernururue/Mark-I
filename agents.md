# Mark-I — Agent Rules

## Project Overview

Mark-I is a two-area project with independent **backend** and **frontend** development streams.

Each area has its own dedicated agent (developer). Agents operate within strict responsibility boundaries.

```
                    Mark-I
                       │
              ┌────────┴────────┐
              ↓                 ↓
           BACKEND           FRONTEND
              │                 │
         backend/           frontend/
              │                 │
        TRACKER.yaml      TRACKER.yaml
              │                 │
              ↓                 ↓
        backend tasks      frontend tasks
              │                 │
              └────────┬────────┘
                       ↓
               docs/TRACKER.yaml
               Global project state
```

---

## Agent Initialization (MANDATORY)

When an agent starts a development session from the project root:

1. Read this file (`agents.md`).
2. Determine the developer's work area.
3. If the work area is not explicitly known, **ask**:

   > "Which part are you working on: **backend** or **frontend**?"

4. Once the developer selects an area:
   - **backend** → read `backend/agents.md`
   - **frontend** → read `frontend/agents.md`

5. The agent MUST then operate **only** inside its assigned responsibility boundary.

The agent must **NOT** silently switch from backend to frontend or vice versa.

If a task requires changes outside the assigned area, **ask the user for explicit permission**.

---

## File Ownership Boundaries

### Backend Agent

**Owns**: `backend/` (all files and subdirectories)

Allowed to modify:
- `backend/` — all implementation files
- `backend/agents.md` — backend agent rules
- `backend/TRACKER.yaml` — backend task tracker
- `backend/docs/` — backend-specific documentation
- `docs/` — shared project documentation, **only** when the documentation workflow requires it

Must **NOT** modify `frontend/` without explicit user permission.

### Frontend Agent

**Owns**: `frontend/` (all files and subdirectories)

Allowed to modify:
- `frontend/` — all implementation files
- `frontend/agents.md` — frontend agent rules
- `frontend/TRACKER.yaml` — frontend task tracker
- `frontend/docs/` — frontend-specific documentation
- `docs/` — shared project documentation, **only** when the documentation workflow requires it

Must **NOT** modify `backend/` without explicit user permission.

### Shared Documentation

`docs/` contains project-level documentation:
- `docs/prd.md` — Product Requirements Document
- `docs/trd.md` — Technical Requirements Document
- `docs/TRACKER.yaml` — Global project state tracker

---

## Tracker Hierarchy

There are **three** tracker levels. All exist from project start.

### 1. `backend/TRACKER.yaml` — Backend Tracker

Tracks **only** backend plans and tasks. Do not put frontend tasks here.

### 2. `frontend/TRACKER.yaml` — Frontend Tracker

Tracks **only** frontend plans and tasks. Do not put backend tasks here.

### 3. `docs/TRACKER.yaml` — Global Project Tracker

Aggregates the state of the entire project. Reflects the high-level status of backend, frontend, and integration. Does **not** duplicate every implementation detail from the area trackers.

```
backend/TRACKER.yaml  ──┐
                        ├──→ docs/TRACKER.yaml
frontend/TRACKER.yaml ──┘
```

The global tracker exists from the start and is always kept in sync as an aggregator.

### Synchronization Rules

- When a major backend milestone is completed → update `backend/TRACKER.yaml` **and** `docs/TRACKER.yaml`.
- When a major frontend milestone is completed → update `frontend/TRACKER.yaml` **and** `docs/TRACKER.yaml`.
- The global tracker must **never** contradict the area trackers.

---

## Documentation & Planning Workflow

Each area uses a structured planning workflow inside its own directory.

### Plan Structure

For a **backend** feature:

```
backend/docs/plans/
└── YYYY-MM-DD-feature-name/
    ├── plan.md               # Overview, goals, architecture, scope
    ├── diagram.excalidraw    # Architecture diagram
    ├── blockers.excalidraw   # Dependency/blocker diagram
    ├── 01-task-name.md       # Task 1: implementation spec
    ├── 02-task-name.md       # Task 2: implementation spec
    └── ...
```

For a **frontend** feature:

```
frontend/docs/plans/
└── YYYY-MM-DD-feature-name/
    ├── plan.md
    ├── diagram.excalidraw
    ├── blockers.excalidraw
    ├── 01-task-name.md
    ├── 02-task-name.md
    └── ...
```

### Plan Requirements

Every plan **MUST** contain:
- `plan.md`
- `diagram.excalidraw`
- `blockers.excalidraw`
- At least one numbered task file

Each plan must be registered in its area's `TRACKER.yaml`.

### TRACKER.yaml Format (Area Trackers)

```yaml
plans:
  - name: feature-name
    path: docs/plans/YYYY-MM-DD-feature-name/
    status: planned              # planned → in-progress → shipped
    created: YYYY-MM-DD
    started:
    shipped:
    tasks:
      - name: task-1-name
        file: 01-task-name.md
        status: pending          # pending → in-progress → done
```

---

## Task Lifecycle

Tasks use: `pending` → `in-progress` → `done`

Plans use: `planned` → `in-progress` → `shipped`

### When starting a task:
- Set task status to `in-progress`
- If this is the first active task, set the parent plan to `in-progress`
- Update the appropriate area `TRACKER.yaml`

### When completing a task:
- Set task status to `done`
- Update the appropriate area `TRACKER.yaml`
- Identify newly unblocked tasks if applicable

### When blocked:
- Leave the task as `in-progress`
- **Explicitly report the blocker** — do NOT silently skip

### At the start of every session:
- Check the relevant `TRACKER.yaml` to understand current progress
- Resume from where the last session left off

---

## Shipping (Move to Systems)

When **all** tasks in a plan are complete:

1. Compile `README.md` from `plan.md` and task files
2. Move architecture diagram to `docs/systems/<system-name>/`
3. Move the plan folder from `plans/` to `systems/`
4. Update `TRACKER.yaml` — set plan status to `shipped` with `shipped: date`

---

## Diagram Maintenance

- Diagrams use **Excalidraw** format (`.excalidraw` JSON files)
- Viewable in VS Code with the Excalidraw extension, or at excalidraw.com
- When creating diagrams: use `create_element` for shapes, then `query_elements` to get all elements, then write to `.excalidraw` file format
- When making architectural changes, update relevant `diagram.excalidraw` files

---

## Key Rules Summary

| Rule | Description |
|------|-------------|
| **Area isolation** | Each agent works only in its assigned area |
| **Cross-area changes** | Require explicit user permission |
| **Session start** | Always check TRACKER.yaml first |
| **Every plan** | Must have plan.md, diagram, blockers, and tasks |
| **Tracker sync** | Area trackers are detailed; global tracker is high-level |
| **No silent skips** | Report blockers explicitly |
| **PRD/TRD** | Must be respected — read before implementation |