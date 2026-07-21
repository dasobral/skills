# Simplify to minimum expression

## Decision

Committed generated plugin trees were the opposite of simplicity: every skill
copied 2–3 times under `plugins/`. That bloat is gone.

## Source of truth (only)

- `core/skills/` + `core/manifest.yaml`
- `adapters/<platform>/<plugin>/` — scaffolding only
- `landing/skills/` — unique ingest

## Generated (gitignored)

- `dist/{cursor,claude,codex}/` via `skills-export export`
- Install assembles the same way into user/project paths

## Not committed

- `plugins/`
- marketplace JSON at repo root
- HTML overview artifacts
