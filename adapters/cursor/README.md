# Cursor adapter

Cursor-specific extensions live here per plugin. The export tool merges:

- `core/skills/` → `<plugin>/skills/`
- `adapters/cursor/<plugin>/agents|hooks|rules` → plugin root
- `adapters/cursor/<plugin>/plugin.json` → overlay for `.cursor-plugin/plugin.json`

Do **not** edit skills under root plugin directories — edit `core/skills/` and run:

```bash
./bin/skills-export sync cursor
```
