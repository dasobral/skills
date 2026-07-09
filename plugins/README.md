# Plugins

Platform-ready plugin trees generated from `core/` + `adapters/`.

| Path | Status |
|------|--------|
| [`cursor/`](./cursor/) | **Ready** — committed Cursor plugins (marketplace sources) |
| Claude / Codex | Generated under `dist/` by `./bin/skills-maintain` (not committed) |

Regenerate Cursor plugins:

```bash
./bin/skills-export sync cursor
```
