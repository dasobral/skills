# Platform Path Conventions

Portable skills use **neutral output paths**. Resolve in this priority order
unless the user specifies otherwise:

## Conventions / requirements files

| Priority | Path | Platforms |
|----------|------|-----------|
| 1 | `docs/CODING_REQUIREMENTS.md` | All (preferred neutral) |
| 2 | `.cursor/CODING_REQUIREMENTS.md` | Cursor |
| 3 | `.claude/CODING_REQUIREMENTS.md` | Claude Code |
| 4 | `CODING_REQUIREMENTS.md` (root) | Fallback |

## Cognitive debt reports

Same pattern: `docs/COGNITIVE_DEBT.md` → `.cursor/` → `.claude/` → root.

## Agent instruction pointers

| Platform | Pointer file | Import in |
|----------|-------------|-----------|
| Cursor | `.cursor/instructions.md` | `AGENTS.md` |
| Claude Code | `.claude/instructions.md` | `CLAUDE.md` |
| Codex | `.agents/instructions.md` | `AGENTS.md` |

Pointer content (all platforms):

```markdown
# Agent Instructions
Before writing code, read the project conventions file.
These requirements are authoritative.
```

## Skill install locations

| Platform | Project | User |
|----------|---------|------|
| Cursor | Plugin bundle or `.cursor/skills/` | `~/.cursor/skills/` |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.agents/skills/` | `~/.codex/skills/` or `~/.agents/skills/` |
| Copilot | `.github/skills/` | User skills dir |
