# Portable Skills Framework

One **portable core**, automatic **ingest from `landing/`**, and **export to Cursor, Claude Code, and Codex**. Stops the copy-paste migration pain.

Ready plugins today are **Cursor-first** under `plugins/cursor/`. Claude and Codex are generated into `dist/` on demand.

## The loop

```
landing/ (any platform)  →  ingest + normalize  →  core/skills/
                              ↓
                    validate + translate
                              ↓
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  plugins/cursor/        dist/claude/          dist/codex/
  (committed)            (generated)           (generated)
```

Interactive overview: [docs/artifacts/skills-framework-overview.html](./docs/artifacts/skills-framework-overview.html)
## Quick start

```bash
# Drop a skill in landing/skills/my-skill/ (SKILL.md + references/)
# Edit landing/registry.yaml → assign my-skill: codecraft

./bin/skills-maintain              # ingest → validate → export all platforms
./bin/skills-install claude        # install flat skills to .claude/skills/
./bin/skills-install codex --user  # install to ~/.codex/skills/
./bin/skills-install cursor --plugins --user   # full plugins → ~/.cursor/plugins/local/
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
| `./bin/skills-export sync cursor` | Regenerate `plugins/cursor/` |
| `./bin/skills-export export all` | Write `dist/claude` + `dist/codex` (+ `dist/cursor`) |
| `./bin/skills-export validate` | Check core vs manifest |
| `./bin/skills-install <platform>` | Copy exports into standard install paths |

## Repo layout

```
core/skills/              ← source of truth (edit or ingest into here)
core/manifest.yaml        ← plugin ↔ skill map
landing/                  ← drop zone for new skills
adapters/cursor/          ← Cursor-only agents, hooks, rules
plugins/cursor/           ← generated Cursor plugins (ready to use)
tools/skills-export/      ← framework CLI
scripts/cron/             ← cron wrapper + install/uninstall
dist/                     ← generated Claude/Codex (and optional Cursor) output
```

## Authoring rules

1. **New skills** → `landing/skills/` (or `incoming/<platform>/`)
2. **Assign plugin** → `landing/registry.yaml` or skill-local `landing.yaml`
3. Run `./bin/skills-maintain`
4. **Direct edits** → `core/skills/` then `sync cursor` + `export all`

## Periodic / autonomous (cron)

Use the maintained wrapper instead of a raw crontab one-liner:

```bash
./scripts/cron/install.sh --dry-run    # preview
./scripts/cron/install.sh              # every 6 hours (default)
./scripts/cron/install.sh --schedule '0 3 * * *'
./scripts/cron/uninstall.sh
```

See [scripts/cron/README.md](./scripts/cron/README.md). Report: `landing/last-maintain.json`.

## Stack coverage

| Platform | Export | Install path |
|----------|--------|--------------|
| **Cursor** | Plugins under `plugins/cursor/` | `~/.cursor/plugins/local/` or marketplace |
| **Claude Code** | `.claude/skills/` bundles in `dist/` | `.claude/skills/` |
| **Codex** | `.agents/skills/` bundles in `dist/` | `.agents/skills/` or `~/.codex/skills/` |

All skills follow the [Agent Skills open standard](https://agentskills.io).

## License

MIT — see [LICENSE](./LICENSE).
