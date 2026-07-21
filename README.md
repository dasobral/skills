# Portable Skills Framework

One **portable core**, one **ingest path** (`landing/skills/`), and **symmetric export** to Cursor, Claude Code, and Codex. Export paths own platform scaffolding; core holds only what is common.

## The loop

```
landing/skills/  →  ingest + normalize  →  core/skills/
                                              ↓
                                    validate + sync
                                              ↓
                     ┌────────────────────────┼────────────────────────┐
                     ▼                        ▼                        ▼
              plugins/cursor/          plugins/claude/          plugins/codex/
              adapters/cursor/         adapters/claude/         adapters/codex/
```

Interactive overview: [docs/artifacts/skills-framework-overview.html](./docs/artifacts/skills-framework-overview.html)

## Quick start

```bash
# Drop a skill in landing/skills/my-skill/ (SKILL.md + references/)
# Edit landing/registry.yaml → assign my-skill: codecraft

./bin/skills-maintain              # ingest → validate → sync all platforms
./bin/skills-install claude --plugins --user
./bin/skills-install codex --plugins --user
./bin/skills-install cursor --plugins --user
```

## Landing zone

| Path | Drop here |
|------|-----------|
| `landing/skills/` | **Only** ingest input — portable Agent Skills |

After successful ingest, items move to `landing/processed/<timestamp>/`.

Platform scaffolding (agents, hooks, rules, manifests) is authored under `adapters/<platform>/`, never ingested.

See [landing/README.md](./landing/README.md).

## Commands

| Command | What it does |
|---------|----------------|
| `./bin/skills-maintain` | Full autonomous pipeline |
| `./bin/skills-export ingest` | Landing → core only |
| `./bin/skills-export sync all` | Regenerate `plugins/{cursor,claude,codex}/` |
| `./bin/skills-export sync <platform>` | Regenerate one platform |
| `./bin/skills-export validate` | Check core and existing generated trees |
| `./bin/skills-export validate <platform>` | Check one platform |
| `./bin/skills-export export all` | Compatibility write under `dist/` |
| `./bin/skills-install <platform>` | Install flat skills |
| `./bin/skills-install <platform> --plugins` | Install native plugins |

## Repo layout

```
core/skills/              ← source of truth (edit or ingest into here)
core/manifest.yaml        ← plugin ↔ skill map + platform flags
landing/skills/           ← unique drop zone
adapters/cursor/          ← Cursor scaffolding
adapters/claude/          ← Claude scaffolding
adapters/codex/           ← Codex scaffolding
plugins/cursor/           ← generated Cursor plugins
plugins/claude/           ← generated Claude plugins
plugins/codex/            ← generated Codex plugins
.cursor-plugin/marketplace.json
.claude-plugin/marketplace.json
.agents/plugins/marketplace.json
tools/skills-export/      ← framework CLI
```

## Authoring rules

1. **New skills** → `landing/skills/`
2. **Assign plugin** → `landing/registry.yaml` or skill-local `landing.yaml`
3. Add platform-only files under `adapters/<platform>/<plugin>/`
4. Run `./bin/skills-maintain` to regenerate all three native trees

Generated `plugins/*/` and marketplace files are committed; do not edit them directly.

## Native Codex trust and setup

The repository Codex marketplace is `.agents/plugins/marketplace.json`. Native installation is explicit:

```bash
./bin/skills-install codex --plugins --project
./bin/skills-install codex --plugins --user
```

Plugin installation copies native plugin files and marketplace metadata, but never installs bundled custom agents. Invoke the plugin's `install-plugin-agents` skill, review its dry-run, confirm the destination, and start a new Codex session after installation.

Treat hooks as executable code. Review each plugin's `hooks/hooks.json` and referenced scripts before enabling it; generation and static validation establish structure and path containment, not trust.

## Claude Code plugins

```bash
./bin/skills-export sync claude
./bin/skills-install claude --plugins --user
# then in Claude Code:
# /plugin marketplace add ~/.claude/marketplaces/dasobral-skills
```

Or add this repository as a marketplace (sources under `./plugins/claude/`).

## Evidence workflow plugins

The five Codex-oriented workflow plugins (also exported to Claude as skill plugins) are:

- `agentic-trust-gate` — repository control-plane and MCP drift evidence;
- `agent-attack-replay` — authorized, isolated attack scenarios and trial ledgers;
- `crypto-change-radar` — cryptographic inventory, semantic deltas, PQC planning, and interoperability evidence;
- `entropy-flight-recorder` — entropy-source qualification and requalification decisions;
- `scientific-claim-ledger` — reproducible run capture and claim-to-evidence review.

They produce evidence records and explicit `unknown`, `not-applicable`, or `evidence-gap` states. They do not certify repository/model safety, cryptographic or entropy adequacy, standards compliance, scientific validity, or release readiness.

## Periodic / autonomous (cron)

```bash
./scripts/cron/install.sh --dry-run
./scripts/cron/install.sh
```

See [scripts/cron/README.md](./scripts/cron/README.md). Report: `landing/last-maintain.json`.

## Stack coverage

| Platform | Export | Install |
|----------|--------|---------|
| **Cursor** | `plugins/cursor/` | `~/.cursor/plugins/local/` or marketplace |
| **Claude Code** | `plugins/claude/` | local marketplace or flat `~/.claude/skills/` |
| **Codex** | `plugins/codex/` | marketplace or flat `.agents/skills/` |

All skills follow the [Agent Skills open standard](https://agentskills.io).

## License

MIT — see [LICENSE](./LICENSE).
