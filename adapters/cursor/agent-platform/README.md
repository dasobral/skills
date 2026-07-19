# Agent Platform

Author and orchestrate multi-agent workflows in Cursor.

## Skills

| Skill | Purpose |
|-------|---------|
| `agent-ste` | Rewrite vague prompts into explicit, checkable agent instructions |
| `create-agent` | Scaffold agent definition `.md` files |
| `orchestrate` | Task graphs, parallel execution, artifact routing |

## Agents

- `orchestrator` — top-level multi-agent coordinator
- `reader`, `analyzer`, `report-writer` — example pipeline agents (see `skills/orchestrate/examples/`)

## Hooks

- `sessionStart` — lists available agents in `agents/` directory

## Quick Start

1. Rewrite the goal with `agent-ste` when the prompt is vague or multi-model
2. Create agents: use `create-agent` skill
3. Place `.md` files in `agents/`
4. Run: use `orchestrate` skill with your task
