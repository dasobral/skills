# Cursor adapter

Cursor-specific extras live here per plugin. Portable skills are in `skills/`.

The extras installer merges:

- `skills/` → assembled plugin `skills/`
- `adapters/cursor/<plugin>/agents|hooks|rules` → plugin root
- `adapters/cursor/<plugin>/plugin.json` → overlay for `.cursor-plugin/plugin.json`

Do **not** edit skill bodies under assembled output. Edit `skills/` and run:

```bash
npx skills add dasobral/skills -a cursor
./bin/skills-install cursor --plugins --user
```
