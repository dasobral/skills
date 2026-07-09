# Landing zone

Drop new skills here from **any platform** (Cursor, Claude Code, Codex, or portable Agent Skills). Run maintenance to ingest into the unified core and re-export everywhere.

## Structure

```
landing/
  registry.yaml          # skill → plugin assignments (edit before ingest)
  skills/                # portable Agent Skills (SKILL.md + references/)
    my-skill/
      SKILL.md
      references/
  incoming/
    cursor/              # Cursor plugin folders (skills + agents/hooks/rules)
      my-plugin/
    claude/              # Claude skill folders or .claude/skills layout
      my-skill/
    codex/               # Codex skill folders or .agents/skills layout
      my-skill/
  processed/             # archived after successful ingest (auto)
```

## Per-skill metadata (optional)

`landing.yaml` inside a skill folder:

```yaml
plugin: codecraft        # target plugin (overrides registry.yaml)
create_plugin: false     # if true + plugin missing, use registry new_plugins
```

## Commands

```bash
# Full pipeline: ingest landing → validate → sync plugins/cursor → export Claude/Codex
./bin/skills-maintain

# Preview without writing
./bin/skills-maintain --dry-run

# Ingest only
./bin/skills-export ingest

# Export only (after manual core edits)
./bin/skills-export sync cursor && ./bin/skills-export export all
```

## Periodic / autonomous use

Prefer the cron helper (PATH, logging, install/uninstall):

```bash
./scripts/cron/install.sh --dry-run
./scripts/cron/install.sh
```

Or a raw crontab line:

```bash
cd /path/to/skills && ./scripts/cron/skills-maintain.sh
```

Or Cursor automation: run `skills-maintain` when `landing/` changes.

See [scripts/cron/README.md](../scripts/cron/README.md).

## Skill requirements

- Directory name = `name` in SKILL.md frontmatter (lowercase-kebab-case)
- Required frontmatter: `name`, `description`
- Follow [Agent Skills](https://agentskills.io/specification) layout

Incoming platform-native skills are **normalized** to portable core on ingest.
