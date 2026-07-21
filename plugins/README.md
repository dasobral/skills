# Plugins

Platform-ready plugin trees generated from `core/` + `adapters/`.

| Path | Status |
|------|--------|
| [`cursor/`](./cursor/) | Generated — Cursor plugins (`.cursor-plugin/`) |
| [`claude/`](./claude/) | Generated — Claude Code plugins (`.claude-plugin/`) |
| [`codex/`](./codex/) | Generated — Codex plugins (`.codex-plugin/`) |

Regenerate:

```bash
./bin/skills-export sync all
./bin/skills-export validate
```

Author portable content in `core/` and platform overlays in `adapters/`; never
edit generated plugin trees directly.

| Marketplace | Path |
|-------------|------|
| Cursor | `.cursor-plugin/marketplace.json` |
| Claude | `.claude-plugin/marketplace.json` |
| Codex | `.agents/plugins/marketplace.json` |
