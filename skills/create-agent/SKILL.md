---
name: create-agent
description: >
  Scaffolds platform-native Cursor Markdown or Codex TOML agent definitions
  through six layers: Role, Inputs, Process, Output contract, Constraints, and
  Integration hooks. Part of Agent Platform plugin. Use when creating agents
  or formalizing multi-agent components.
---

# Create Agent

Scaffold a complete native agent definition for Cursor or Codex.

## Step 1 — Resolve Platform, Name, and Path

Use the user's explicit target when provided. Otherwise infer the platform only
from unambiguous repository configuration. For an unknown platform, ask which
target to use.

Normalize the name to `lowercase-kebab-case`, then select the native path:

| Platform | Definition | Default path |
|----------|------------|--------------|
| Cursor | Markdown | `./agents/<name>.md` or the plugin's `agents/` |
| Codex | TOML | `.codex/agents/<name>.toml` |

## Step 2 — Load Conventions

Read `references/agent-conventions.md`, then load the native template:

- Cursor: `templates/agent-definition.md`
- Codex: `templates/agent-definition.toml`

## Step 3 — Gather Six Layers

| Layer | Capture |
|-------|---------|
| Role | Identity, purpose, tone, scope |
| Inputs | name, type, required, description per parameter |
| Process | Numbered imperative steps (3–15) |
| Output | One value from the exact output vocabulary |
| Constraints | Read-only, scope limits, tool restrictions |
| Integration | Parent orchestrator, artifact routing, dependency handoffs |

The exact output vocabulary is: `json_object`, `markdown_document`, `file_write`, `inline_text`, or `tool_call_sequence`.

## Step 4 — Render the Native Definition

For Cursor, use Markdown with frontmatter:

```yaml
---
name: agent-name
description: One-line trigger description for agent discovery.
model: fast  # optional: fast | inherit | specific model slug
---
```

For Codex, write valid TOML with all required keys:

```toml
name = "agent-name"
description = "One-line discovery description."
developer_instructions = """
State the role, inputs, process, output contract, constraints, and handoffs.
"""
```

Do not hard-code a Codex model or sandbox policy. Put the complete behavioral
contract in `developer_instructions`.

## Step 5 — Write File

Write the complete definition to the resolved native path. Include an example
from `examples/` only for Cursor when helpful.

## Step 6 — Validate

- [ ] File parses as Markdown frontmatter or TOML for the selected platform
- [ ] Definition has non-empty `name` and `description`
- [ ] Codex definition has non-empty `developer_instructions`
- [ ] At least one input parameter defined
- [ ] Output contract is machine-parseable
- [ ] Integration contract defines parent and artifact handoffs

## Rules

- Match the `orchestrate` skill's handoff contract without assuming a specific
  delegation API
- Preserve platform-native syntax and paths
- See `references/agent-conventions.md` for naming and structure
