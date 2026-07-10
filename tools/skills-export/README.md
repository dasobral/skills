# skills-export

Generate and validate native Cursor/Codex plugins plus portable flat-skill exports.

## Quick start (no install)

From repo root:

```bash
chmod +x bin/skills-export
./bin/skills-export validate
./bin/skills-export sync cursor      # regenerate 6 plugins/cursor/ entries
./bin/skills-export sync codex       # regenerate 11 plugins/codex/ entries
./bin/skills-export export all       # write compatibility output under dist/
```

## Install (optional)

```bash
pip install -e tools/skills-export
skills-export validate
```

## Commands

| Command | Purpose |
|---------|---------|
| `validate` | Check manifest/core plus existing native Cursor and Codex output |
| `validate cursor` | Check generated Cursor plugins and marketplace |
| `validate codex` | Check Codex manifests, paths, skills, hooks, agents, and marketplace |
| `list` | List plugins and skills |
| `sync cursor` | Regenerate `plugins/cursor/` from `core/` + `adapters/cursor/` |
| `sync codex` | Regenerate `plugins/codex/` and `.agents/plugins/marketplace.json` |
| `export cursor` | Write Cursor plugins to `dist/cursor/` |
| `export claude` | Write Claude compatibility packages and flat skills |
| `export codex` | Write flat skills to `dist/codex/skills/` |
| `export all` | All three platforms |
| `ingest` | Landing → core |
| `maintain` | Ingest, validate, sync both native trees, then export flat skills |

## Architecture

```
core/
  manifest.yaml          # plugin ↔ skill mapping (source of truth)
  skills/<name>/         # portable SKILL.md + references (Agent Skills standard)
  references/            # platform-paths, platform-orchestration

adapters/
  cursor/<plugin>/       # agents, hooks, rules, plugin.json overlay
  claude/                # Claude compatibility templates
  codex/<plugin>/        # Codex manifests, agents, hooks, workflow overlay

plugins/cursor/          # 6 generated, committed Cursor plugins
plugins/codex/           # 11 generated, committed Codex plugins
.cursor-plugin/marketplace.json
.agents/plugins/marketplace.json
dist/claude/skills/      # generated flat Claude skills
dist/codex/skills/       # generated flat Codex skills
scripts/cron/            # cron wrapper for maintain
```

**Edit portable skills in `core/skills/` only.** Put platform-specific
components in the matching adapter and run both native sync commands before
reviewing generated changes.

## Installation and trust

`./bin/skills-install codex --plugins --project` or `--user` copies native
plugins and merges marketplace metadata into the selected isolated scope. It
does not install bundled agent templates. The generated
`install-plugin-agents` skill requires a dry-run, conflict review, explicit
confirmation, and a new Codex session.

Review Codex hook JSON and scripts as executable code before enabling them.
Validators prove structural consistency and containment, not behavioral trust.
Workflow contracts preserve evidence gaps and non-claims; they do not turn
agent judgment into certification.

## Tests

```bash
python3 -m pytest tools/skills-export/tests -m "not integration" -v
python3 -m pytest tools/skills-export/tests/integration/test_codex_marketplace_cli.py -v -rs
```

The integration module is marked `integration` and uses temporary `HOME`,
`CODEX_HOME`, XDG directories, and repository data. Its Codex CLI test covers
only the officially documented local marketplace `add` and `list` commands and
skips precisely when those commands are unavailable. It probes help for future
advertised plugin `install` or `list` commands without guessing arguments.
Codex CLI currently delegates local plugin installation to the ChatGPT desktop
app, so local Python tests separately parse manifests, skills, and hooks and
exercise project-scoped agent-template installation. No test writes real user
configuration or claims native CLI plugin loading.

Cursor regression tests use
`tests/fixtures/cursor-origin-main-sha256.json`, pinned to an explicit
`origin/main` commit. It hashes every non-skill component and plugin manifest
individually and every unchanged skill tree. Only `create-agent` (Codex TOML
targeting), `write-conformant-code` (portable convention references), and
`cpp-engineer` (portable C++/QKD guidance) are allowlisted because those
portable changes deliberately propagate to both generated platforms.
