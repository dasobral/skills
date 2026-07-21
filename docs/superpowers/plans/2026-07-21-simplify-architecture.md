# Implementation plan: simplify architecture

## Tasks

1. Simplify `ingest.py` to `landing/skills/` only; remove incoming paths.
2. Add Claude helpers in `manifest.py`; rewrite `exporters/claude.py` to write `plugins/claude/` + `.claude-plugin/marketplace.json`.
3. Add `validate_claude.py`; wire `cli.py` + `maintain.py` for symmetric sync/validate.
4. Update `core/manifest.yaml` with `claude:` on every plugin.
5. Seed `adapters/claude/<plugin>/` with plugin.json overlays + READMEs where useful (minimal).
6. Update install script for `claude --plugins`.
7. Remove `landing/incoming/`; update README, landing README, plugins README, adapters README, CHANGELOG.
8. Generate `plugins/claude/` via sync; run tests; fix fallout.
