# skills-export

Generate and validate native Cursor, Claude Code, and Codex plugins from a portable core.

## Quick start

```bash
./bin/skills-export validate
./bin/skills-export sync all
./bin/skills-export export all       # optional compatibility output under dist/
```

## Architecture

```
landing/skills/          # unique ingest
core/                    # portable skills + manifest
adapters/<platform>/     # scaffolding owned by each export path
plugins/<platform>/      # generated native plugins (cursor, claude, codex)
```

**Edit portable skills in `core/skills/` only.** Put platform-specific
components in the matching adapter and run `sync` before reviewing generated changes.

## Commands

| Command | Purpose |
|---------|---------|
| `validate` | Check core plus existing native output |
| `validate <platform>` | Check one of cursor / claude / codex |
| `sync <platform\|all>` | Regenerate `plugins/<platform>/` |
| `export <platform\|all>` | Write compatibility output under `dist/` |
| `ingest` | `landing/skills/` → core |
| `maintain` | Ingest, validate, sync all three platforms |

## Tests

```bash
python3 -m pytest tools/skills-export/tests -m "not integration" -v
```
