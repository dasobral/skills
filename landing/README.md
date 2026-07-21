# Landing zone

Drop portable skills here. There is **one** ingest path.

## Structure

```
landing/
  registry.yaml          # skill → plugin assignments
  skills/                # ONLY ingest input (SKILL.md + references/)
    my-skill/
      SKILL.md
      references/
      landing.yaml       # optional: plugin override
  processed/             # archived after successful ingest
```

## Commands

```bash
./bin/skills-maintain              # ingest → validate → sync all platforms
./bin/skills-maintain --dry-run
./bin/skills-export ingest
./bin/skills-export sync all
```

Native outputs are committed at `plugins/cursor/`, `plugins/claude/`, and
`plugins/codex/`. Marketplaces live at `.cursor-plugin/marketplace.json`,
`.claude-plugin/marketplace.json`, and `.agents/plugins/marketplace.json`.

## Skill requirements

- Directory name = `name` in SKILL.md frontmatter (lowercase-kebab-case)
- Required frontmatter: `name`, `description`
- Follow [Agent Skills](https://agentskills.io/specification) layout

Platform-specific agents, hooks, and manifests belong in
`adapters/<platform>/<plugin>/`, not in landing skill content.
