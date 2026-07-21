# Portable Skills

Portable Agent Skills in `core/`. Platform scaffolding in `adapters/`. Nothing else is source of truth.

```
landing/skills/  →  ingest  →  core/skills/
                                   + adapters/<platform>/
                                   ↓
                              assemble → dist/ (gitignored)
                                   ↓
                              skills-install
```

## Use

```bash
# Add a skill
# 1. drop landing/skills/my-skill/SKILL.md
# 2. map it in landing/registry.yaml
./bin/skills-maintain

# Install
./bin/skills-install cursor --plugins --user
./bin/skills-install claude --plugins --user
./bin/skills-install codex --plugins --project
```

## Layout

| Path | Role |
|------|------|
| `core/skills/` | Portable skills (edit here) |
| `core/manifest.yaml` | Plugin ↔ skill map |
| `adapters/{cursor,claude,codex}/` | Agents, hooks, manifests |
| `landing/skills/` | Ingest drop zone |
| `dist/` | Generated output (gitignored) |
| `tools/skills-export/` | CLI |

Generated plugin trees are **never committed**. Assemble on demand.

## Commands

| Command | Action |
|---------|--------|
| `./bin/skills-export validate` | Check core |
| `./bin/skills-export export` | Write `dist/{cursor,claude,codex}/` |
| `./bin/skills-export ingest` | Landing → core |
| `./bin/skills-maintain` | Ingest + validate + export |
| `./bin/skills-install <platform> [--plugins]` | Assemble into install paths |

MIT — see [LICENSE](./LICENSE).
