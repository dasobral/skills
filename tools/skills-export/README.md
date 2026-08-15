# skills-export

Validate `skills/` + `core/manifest.yaml`, write Agent Plugins 1.0 packages under `plugins/<family>/`, and assemble Cursor/Codex extras into `dist/`.

```bash
./bin/skills-export validate
./bin/skills-export export
./bin/skills-maintain
```

Portable skills are installed with `npx skills add dasobral/skills`. Native extras stay gitignored under `dist/`.
