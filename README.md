# Portable Skills Framework

One **portable core**, automatic **ingest from `landing/`**, and **export to Cursor, Claude Code, and Codex**. Six Cursor plugins and eleven Codex plugins are committed native outputs; flat skills remain available for compatibility.

## The loop

```
landing/ (any platform)  →  ingest + normalize  →  core/skills/
                              ↓
                    validate + translate
                              ↓
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  plugins/cursor/      plugins/codex/       dist/*/skills/
  6 native plugins     11 native plugins    flat exports
```

Interactive overview: [docs/artifacts/skills-framework-overview.html](./docs/artifacts/skills-framework-overview.html)
## Quick start

```bash
# Drop a skill in landing/skills/my-skill/ (SKILL.md + references/)
# Edit landing/registry.yaml → assign my-skill: codecraft

./bin/skills-maintain              # ingest → validate → export all platforms
./bin/skills-install claude        # install flat skills to .claude/skills/
./bin/skills-install codex --user  # install flat skills to ~/.codex/skills/
./bin/skills-install cursor --plugins --user   # full plugins → ~/.cursor/plugins/local/
./bin/skills-install codex --plugins --project # native plugins + marketplace
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
| `./bin/skills-export sync codex` | Regenerate `plugins/codex/` and `.agents/plugins/marketplace.json` |
| `./bin/skills-export export all` | Write flat/compatibility output under `dist/` |
| `./bin/skills-export validate` | Check core and existing generated platform trees |
| `./bin/skills-export validate codex` | Check native Codex manifests, paths, skills, hooks, agents, and marketplace |
| `./bin/skills-install <platform>` | Copy flat skills into standard install paths |

## Repo layout

```
core/skills/              ← source of truth (edit or ingest into here)
core/manifest.yaml        ← plugin ↔ skill map
landing/                  ← drop zone for new skills
adapters/cursor/          ← Cursor-only agents, hooks, rules
adapters/codex/           ← Codex manifests, agents, hooks, workflow overlays
plugins/cursor/           ← 6 generated, committed Cursor plugins
plugins/codex/            ← 11 generated, committed Codex plugins
.cursor-plugin/marketplace.json ← Cursor marketplace
.agents/plugins/marketplace.json ← Codex marketplace
tools/skills-export/      ← framework CLI
scripts/cron/             ← cron wrapper + install/uninstall
dist/claude/              ← generated Claude flat skills and compatibility output
dist/codex/skills/        ← generated Codex flat skills
```

## Authoring rules

1. **New skills** → `landing/skills/` (or `incoming/<platform>/`)
2. **Assign plugin** → `landing/registry.yaml` or skill-local `landing.yaml`
3. Add platform-only files under `adapters/<platform>/<plugin>/`
4. Run `./bin/skills-maintain` to regenerate both native trees and flat exports

Generated `plugins/cursor/`, `plugins/codex/`, and both marketplace files are committed; do not edit them directly.

## Native Codex trust and setup

The repository Codex marketplace is `.agents/plugins/marketplace.json`. Native installation is explicit:

```bash
./bin/skills-install codex --plugins --project
./bin/skills-install codex --plugins --user
```

Plugin installation copies native plugin files and marketplace metadata, but never installs bundled custom agents. Invoke the plugin's `install-plugin-agents` skill, review its dry-run, confirm the destination, and start a new Codex session after installation.

Treat hooks as executable code. Review each plugin's `hooks/hooks.json` and referenced scripts before enabling it; generation and static validation establish structure and path containment, not trust.

## Evidence workflow plugins

The five Codex-only workflow plugins are:

- `agentic-trust-gate` — repository control-plane and MCP drift evidence;
- `agent-attack-replay` — authorized, isolated attack scenarios and trial ledgers;
- `crypto-change-radar` — cryptographic inventory, semantic deltas, PQC planning, and interoperability evidence;
- `entropy-flight-recorder` — entropy-source qualification and requalification decisions;
- `scientific-claim-ledger` — reproducible run capture and claim-to-evidence review.

They produce evidence records and explicit `unknown`, `not-applicable`, or `evidence-gap` states. They do not certify repository/model safety, cryptographic or entropy adequacy, standards compliance, scientific validity, or release readiness. Optional unavailable tools must remain evidence gaps, and users remain responsible for authorization, secrets, privacy, sandboxing, and expert review.

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
| **Cursor** | 6 native plugins under `plugins/cursor/` | `~/.cursor/plugins/local/` or marketplace |
| **Claude Code** | Flat skills under `dist/claude/skills/` | `.claude/skills/` |
| **Codex** | 11 native plugins under `plugins/codex/`; flat skills under `dist/codex/skills/` | repository/user marketplace or `.agents/skills/` / `~/.codex/skills/` |

All skills follow the [Agent Skills open standard](https://agentskills.io).

## License

MIT — see [LICENSE](./LICENSE).
