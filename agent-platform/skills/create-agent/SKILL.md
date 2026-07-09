---
name: create-agent
description: >
  Scaffolds Cursor agent definition files (.md) through six layers: Role,
  Inputs, Process, Output contract, Constraints, and Integration hooks.
  Part of Agent Platform plugin. Use when creating agents, scaffolding
  subagent definitions, or formalizing multi-agent components.
---

# Create Agent

Scaffold a complete agent definition file (`{agent-name}.md`) for use in
`agents/` directories or multi-agent pipelines.

## Step 1 — Resolve Name & Path

Normalize to `lowercase-kebab-case`. Default output: `./agents/{name}.md`
or plugin's `agents/` if present.

## Step 2 — Load Conventions

Read `references/agent-conventions.md` and `templates/agent-definition.md`.

## Step 3 — Gather Six Layers

| Layer | Capture |
|-------|---------|
| Role | Identity, purpose, tone, scope |
| Inputs | name, type, required, description per parameter |
| Process | Numbered imperative steps (3–15) |
| Output | json_object / markdown_document / file_write / inline_text |
| Constraints | Read-only, scope limits, tool restrictions |
| Integration | Parent orchestrator hooks, artifact routing, subagent_type |

Use Cursor frontmatter format:
```yaml
---
name: agent-name
description: One-line trigger description for agent discovery.
model: fast  # optional: fast | inherit | specific model slug
---
```

## Step 4 — Write File

Output complete `.md` to resolved path. Include example from `examples/` if helpful.

## Step 5 — Validate

- [ ] Frontmatter has `name` and `description`
- [ ] At least one input parameter defined
- [ ] Output contract is machine-parseable
- [ ] Integration section references orchestrate skill handoff format

## Rules

- Agents are consumed by `orchestrate` skill — match its contract schema
- Prefer Task-tool subagents for parallel work in modern Cursor workflows
- See `references/agent-conventions.md` for naming and structure
