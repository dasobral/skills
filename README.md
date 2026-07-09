# Portable Skills

A **portable agent skills core** with a compatibility export layer for **Cursor**, **Claude Code**, and **Codex**. One source of truth in `core/skills/`; platform-specific packaging is generated.

## Architecture

```
core/
  manifest.yaml              # plugin ↔ skill mapping (edit this)
  skills/<name>/SKILL.md     # portable skills (Agent Skills standard)
  references/                # platform-paths, platform-orchestration

adapters/
  cursor/<plugin>/           # agents, hooks, rules (Cursor-only)
  claude/                    # export notes
  codex/

tools/skills-export/         # export CLI
bin/skills-export            # repo-local launcher

codecraft/ …                 # Cursor plugins (generated — run sync)
dist/                        # Claude/Codex exports (generated)
```

**Yes, this makes sense:** skills were born in Claude Code, we turned them into Cursor plugins, and now the core is platform-neutral with thin adapters on top.

## Quick start

```bash
# Validate portable core
./bin/skills-export validate

# Regenerate Cursor plugins at repo root (after editing core/)
./bin/skills-export sync cursor

# Export all platforms to dist/
./bin/skills-export export all
```

## Install per platform

### Cursor (marketplace or local)

```bash
./bin/skills-export sync cursor
cp -r codecraft ~/.cursor/plugins/local/codecraft
```

Includes skills + agents + hooks + rules.

### Claude Code

```bash
./bin/skills-export export claude
cp -r dist/claude/bundles/codecraft/.claude/skills/* .claude/skills/
# optional: cp dist/claude/bundles/codecraft/CLAUDE.md .
```

Or flat install: `cp -r dist/claude/skills/* ~/.claude/skills/`

### Codex

```bash
./bin/skills-export export codex
cp -r dist/codex/bundles/codecraft/.agents/skills/* .agents/skills/
```

Or: `cp -r dist/codex/skills/* ~/.codex/skills/`

## Plugins

| Plugin | Skills | Cursor extras |
|--------|--------|---------------|
| **codecraft** | analyze, write, review, cognitive debt | agents, hooks, rules |
| **cpp-qkd-toolkit** | cpp-engineer, cpp-review | agents, hooks, rules |
| **agent-platform** | create-agent, orchestrate | agents, hooks |
| **aos-stack** | local-inference, rust-systems | agents, hooks |
| **scientific-computing** | platform-architect | agents |
| **career-writer** | career-documents | agents |

## Authoring workflow

1. Edit skill in `core/skills/<name>/`
2. Update `core/manifest.yaml` if adding/remapping plugins
3. Edit Cursor-only bits in `adapters/cursor/<plugin>/` (agents, hooks, rules)
4. `./bin/skills-export validate`
5. `./bin/skills-export sync cursor` (before commit)
6. `./bin/skills-export export all` (optional, for Claude/Codex releases)

## Portability

| Component | Portable | Notes |
|-----------|----------|-------|
| `core/skills/` | Yes | [Agent Skills](https://agentskills.io) standard |
| `core/references/platform-*.md` | Yes | Injected into exports |
| `adapters/cursor/` | Cursor only | agents, hooks, rules |
| Generated Claude/Codex bundles | Yes | Standard install paths |

See [tools/skills-export/README.md](./tools/skills-export/README.md) for CLI details.

## License

MIT — see [LICENSE](./LICENSE).
