# Portable Skills

Portable Agent Skills and Agent Plugins live here. The Vercel CLI installs skills. This repo is not a skills package manager.

```
landing/skills/  →  ingest  →  skills/
                                 + core/manifest.yaml
                                 + plugins/<family>/plugin.json
                                 ↓
                            adapters (Cursor/Codex extras)
                                 ↓
                            skills-install --plugins
```

## Use

```bash
# Install portable skills (Cursor, Claude Code, Codex, and 70+ other agents)
npx skills add dasobral/skills
npx skills add dasobral/skills -g -a cursor -a claude-code -a codex -y
npx skills add dasobral/skills --list

# Optional: Cursor or Codex extras (agents, hooks, rules)
./bin/skills-install cursor --plugins --user
./bin/skills-install codex --plugins --project
```

Set `DISABLE_TELEMETRY=1` to opt out of skills CLI telemetry.

Claude Code has no extras in this repo. Install Claude skills with `npx skills add`.

## Layout

| Path | Role |
|------|------|
| `skills/` | Portable Agent Skills (edit here; well-known discovery path) |
| `core/manifest.yaml` | Plugin family ↔ skill map |
| `plugins/<family>/` | Agent Plugins 1.0.0 packages (`plugin.json` + skill links) |
| `adapters/{cursor,codex}/` | Agents, hooks, rules (not portable) |
| `landing/skills/` | Ingest drop zone |
| `dist/` | Generated Cursor/Codex extras (gitignored) |

Generated native extras are **never committed**. Portable plugin manifests are.

## Commands

| Command | Action |
|---------|--------|
| `npx skills add dasobral/skills` | Install skills via the Vercel CLI |
| `./bin/skills-export validate` | Check skills, manifest, and Agent Plugins packages |
| `./bin/skills-export export` | Write `plugins/<family>/` and `dist/{cursor,claude,codex}/` |
| `./bin/skills-export ingest` | Landing → `skills/` |
| `./bin/skills-maintain` | Ingest + validate + export |
| `./bin/skills-install cursor\|codex --plugins` | Assemble extras into install paths |

MIT — see [LICENSE](./LICENSE).
