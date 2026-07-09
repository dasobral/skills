# Agent Platform

Author and orchestrate multi-agent workflows in Cursor.

## Skills

| Skill | Purpose |
|-------|---------|
| `create-agent` | Scaffold agent definition `.md` files |
| `orchestrate` | Task graphs, parallel execution, artifact routing |

## Agents

- `orchestrator` — top-level multi-agent coordinator
- `reader`, `analyzer`, `report-writer` — example pipeline agents (see `skills/orchestrate/examples/`)

## Hooks

- `sessionStart` — lists available agents in `agents/` directory

## Quick Start

1. Create agents: use `create-agent` skill
2. Place `.md` files in `agents/`
3. Run: use `orchestrate` skill with your task
