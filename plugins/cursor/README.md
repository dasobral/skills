# Generated Cursor plugins

Six ready-to-use **Cursor** plugins assembled from `core/skills/` +
`adapters/cursor/`.

```bash
./bin/skills-export sync cursor   # regenerate this tree
# or
./bin/skills-maintain
```

Do **not** edit skills here — edit `core/skills/` (or drop into `landing/`) and
re-sync.

Eleven native Codex plugins are committed separately under `plugins/codex/`.
Flat Claude and Codex skill exports are generated under `dist/`.

## Install locally

```bash
# Symlink into Cursor local plugins
ln -s "$(pwd)/plugins/cursor/codecraft" ~/.cursor/plugins/local/codecraft

# Or install flat skills from dist after maintain:
./bin/skills-maintain
./bin/skills-install cursor --user
```

Marketplace discovery uses `.cursor-plugin/marketplace.json` at the repo root (`source: plugins/cursor/<name>`).
