# C++ QKD Toolkit

Production C++ for quantum key distribution ground-segment and defense systems.

## Skills

| Skill | Purpose |
|-------|---------|
| `cpp-engineer` | Write, design, and build production C++ |
| `cpp-review` | Unified review with lenses: `--realtime`, `--security`, `--full` |

Consolidates the former `cpp-production-engineer`, `cpp-realtime-reviewer`, and `qkd-security-engineer` skills.

## Agents

- `cpp-realtime-reviewer` — concurrency and hot-path subagent
- `cpp-security-reviewer` — QKD/crypto security subagent

## Rules

- `cpp-qkd-standards.mdc` — auto-applies to C++ files

## Hooks

- `afterFileEdit` — hints security review for sensitive C++ symbols
