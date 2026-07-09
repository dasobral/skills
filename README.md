# Portable Skills Framework

One **portable core**, automatic **ingest from `landing/`**, and **export to Cursor, Claude Code, and Codex**. Stops the copy-paste migration pain.

## The loop

```
landing/ (any platform)  →  ingest + normalize  →  core/skills/
                              ↓
                    validate + translate
                              ↓
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    Cursor plugins      Claude bundles        Codex bundles
    (repo root)         dist/claude/          dist/codex/
```

## Quick start

```bash
# Drop a skill in landing/skills/my-skill/ (SKILL.md + references/)
# Edit landing/registry.yaml → assign my-skill: codecraft

./bin/skills-maintain              # ingest → validate → export all platforms
./bin/skills-install claude        # install flat skills to .claude/skills/
./bin/skills-install codex --user  # install to ~/.codex/skills/
```

## Landing zone

| Path | Drop here |
|------|-----------|
| `landing/skills/` | Portable Agent Skills (any origin) |
| `landing/incoming/claude/` | Claude-native skill folders |
| `landing/incoming/codex/` | Codex-native skill folders |
| `landing/incoming/cursor/` | Full Cursor plugin folders |

After successful ingest, items move to `landing/processed/<timestamp>/`.

See [landing/README.md](./landing/README.md).

## Commands

| Command | What it does |
|---------|----------------|
| `./bin/skills-maintain` | Full autonomous pipeline |
| `./bin/skills-export ingest` | Landing → core only |
| `./bin/skills-export translate` | Same as maintain |
| `./bin/skills-export sync cursor` | Regenerate Cursor plugins at repo root |
| `./bin/skills-export export all` | Write `dist/claude` + `dist/codex` |
| `./bin/skills-export validate` | Check core vs manifest |
| `./bin/skills-install <platform>` | Copy `dist/` into standard install paths |

## Repo layout

```
core/skills/              ← source of truth (edit or ingest into here)
core/manifest.yaml        ← plugin ↔ skill map
landing/                  ← drop zone for new skills
adapters/cursor/          ← Cursor-only agents, hooks, rules
codecraft/ …              ← generated Cursor plugins
tools/skills-export/      ← framework CLI
dist/                     ← generated Claude/Codex output
```

## Authoring rules

1. **New skills** → `landing/skills/` (or `incoming/<platform>/`)
2. **Assign plugin** → `landing/registry.yaml` or skill-local `landing.yaml`
3. Run `./bin/skills-maintain`
4. **Direct edits** → `core/skills/` then `sync cursor` + `export all`

## Periodic / autonomous

```bash
# cron: every 6 hours
0 */6 * * * cd /path/to/skills && ./bin/skills-maintain >> landing/maintain.log 2>&1
```

Report written to `landing/last-maintain.json` after each run.

## Stack coverage

| Platform | Export | Install path |
|----------|--------|--------------|
| **Cursor** | Plugins with agents/hooks/rules | `~/.cursor/plugins/local/` or marketplace |
| **Claude Code** | `.claude/skills/` bundles | `.claude/skills/` |
| **Codex** | `.agents/skills/` bundles | `.agents/skills/` or `~/.codex/skills/` |

All skills follow the [Agent Skills open standard](https://agentskills.io).

## License

MIT — see [LICENSE](./LICENSE).
