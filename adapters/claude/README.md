# Claude Code adapter

Platform scaffolding for Claude Code plugins. The exporter owns assembly:

```
core/skills/ + adapters/claude/<plugin>/  →  plugins/claude/<plugin>/
```

Each generated plugin has:

- `.claude-plugin/plugin.json` — from manifest + optional `plugin.json` overlay
- `skills/` — portable core skills
- optional `agents/`, `hooks/`, `commands/`, `.mcp.json` when present here

Author scaffolding here. Do not put portable skill content in adapters.
