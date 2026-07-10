# Platform Orchestration Patterns

Portable skills describe **what** to parallelize, not **how** per platform.

## Parallel module review

When scope exceeds ~5 files or ~2000 LOC:

1. Split by module or directory
2. Run one reviewer worker per module **in parallel**
3. Synthesize into a single report (deduplicate findings)

| Platform | Mechanism |
|----------|-----------|
| **Cursor** | `Task` tool — multiple calls in one message; custom agents from plugin |
| **Claude Code** | `Agent` tool or subagent definitions in `.claude/agents/` |
| **Codex** | Subagents via `AGENTS.md` or multi-session handoff |
| **Generic** | Sequential review if parallel workers unavailable |

## Parallel explore + collect

For orchestration plans needing git diff + file contents:

| Platform | Mechanism |
|----------|-----------|
| **Cursor** | `Task(subagent_type: shell)` + `Task(subagent_type: explore)` in parallel |
| **Claude Code** | Bash tool + Explore agent in parallel |
| **Codex** | Shell + read tools in one turn or parallel sessions |

## Cloud vs local routing

See `local-inference` skill. Reasoning-heavy tasks → cloud model.
Atomic transforms → local executor when VRAM permits.
