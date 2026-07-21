# Simplify portable skills architecture

## Goal

Simplicity above all. One ingest path. Core holds only what is common. Each export path owns its scaffolding. Cursor, Claude Code, and Codex are treated symmetrically.

## Problems

1. **Multiple ingest paths** — `landing/skills/`, `landing/incoming/{claude,codex,cursor}/`, with special Cursor-plugin unpacking into adapters.
2. **Claude asymmetry** — Cursor and Codex get committed `plugins/<platform>/` + adapters + sync/validate; Claude only got ephemeral `dist/claude/` flat/bundles.
3. **Blurred ownership** — ingest sometimes wrote adapter scaffolding; exporters sometimes invented Claude-only bundle shapes.

## Principles

1. **Unique ingest** — only `landing/skills/<skill>/`.
2. **Core = common** — portable Agent Skills, shared references, plugin↔skill manifest.
3. **Export paths own scaffolding** — `adapters/<platform>/<plugin>/` holds agents, hooks, rules, manifests, READMEs. Exporters assemble `plugins/<platform>/`.
4. **Symmetric platforms** — same loop for cursor, claude, and codex: core + adapters → plugins → marketplace → validate → install.

## Target layout

```
landing/
  skills/<skill>/          # ONLY ingest input
  registry.yaml
  processed/               # archive after ingest

core/
  skills/                  # portable content
  references/              # injected on export
  manifest.yaml            # plugins, skills, per-platform flags

adapters/
  cursor/<plugin>/         # Cursor scaffolding
  claude/<plugin>/         # Claude scaffolding (optional overlays)
  codex/<plugin>/          # Codex scaffolding

plugins/
  cursor/<plugin>/         # generated (.cursor-plugin/)
  claude/<plugin>/         # generated (.claude-plugin/)
  codex/<plugin>/          # generated (.codex-plugin/)

.cursor-plugin/marketplace.json
.claude-plugin/marketplace.json
.agents/plugins/marketplace.json
```

`dist/` remains an optional flat-skill compatibility export, not the primary Claude path.

## Ingest (unique)

1. Scan `landing/skills/` for directories with `SKILL.md`.
2. Validate + normalize to portable core.
3. Assign plugin via `landing.yaml` or `landing/registry.yaml`.
4. Archive to `landing/processed/<timestamp>/`.
5. Never write adapters. Platform scaffolding is authored under `adapters/<platform>/` only.

Remove `landing/incoming/`.

## Export (symmetric)

For each platform with a block in the manifest plugin entry:

| Step | Cursor | Claude | Codex |
|------|--------|--------|-------|
| Skills from core | yes | yes | yes |
| Scaffolding from adapters | agents/hooks/rules | agents/hooks/… | agents/hooks/… |
| Manifest dir | `.cursor-plugin/` | `.claude-plugin/` | `.codex-plugin/` |
| Output | `plugins/cursor/` | `plugins/claude/` | `plugins/codex/` |
| Marketplace | `.cursor-plugin/marketplace.json` | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` |

Claude plugins follow the Claude Code plugin format: `.claude-plugin/plugin.json` + `skills/` at plugin root. Marketplace sources use `./plugins/claude/<name>`.

Manifest: every exported plugin declares the platforms it supports (`cursor:`, `claude:`, `codex:`). Claude receives the same plugin set as Codex (all plugins that declare `claude:`).

## Pipeline

```
landing/skills → ingest → core/
                              ↓
                         validate core
                              ↓
              sync cursor | claude | codex
                              ↓
                    validate platforms
                              ↓
              optional: export flat dist/
```

CLI symmetry:

- `skills-export sync {cursor,claude,codex,all}`
- `skills-export validate [{cursor,claude,codex}]`
- `skills-export maintain` runs ingest + sync all three + validate
- `skills-install {cursor,claude,codex} --plugins` installs from `plugins/<platform>/`

## Non-goals

- Unifying Cursor/Codex/Claude adapter file formats (each platform keeps native shapes).
- Moving skill content into adapters.
- Auto-deriving agents from skills.
- Changing portable skill semantics inside `core/skills/`.

## Success criteria

1. One documented ingest path; `incoming/` gone.
2. `plugins/claude/` generated and committed like the other two.
3. No Claude-only bundle/export special case required for the primary path.
4. Maintain/sync/validate/install treat all three platforms the same way.
5. Existing Cursor and Codex generated trees remain valid; tests pass.
