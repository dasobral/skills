# Cron maintenance for the portable skills framework

Install a crontab entry that runs `bin/skills-maintain` on a schedule: ingest `landing/` → validate → export Cursor / Claude / Codex.

## Quick start

```bash
# Optional: copy and edit defaults
cp scripts/cron/config.env.example scripts/cron/config.env

# Preview the crontab line
./scripts/cron/install.sh --dry-run

# Install (writes scripts/cron/config.env + crontab)
./scripts/cron/install.sh

# Or customize
./scripts/cron/install.sh --schedule '0 3 * * *' --repo /absolute/path/to/skills
```

Verify:

```bash
crontab -l
./scripts/cron/skills-maintain.sh   # one manual run
tail -50 landing/maintain.log
cat landing/last-maintain.json
```

Uninstall:

```bash
./scripts/cron/uninstall.sh
```

## What gets installed

One marked block in your user crontab:

```cron
# skills-framework-maintain
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
0 */6 * * * /absolute/path/to/skills/scripts/cron/skills-maintain.sh
```

The wrapper:

1. `cd`s to the repo (absolute path)
2. Checks PyYAML is importable
3. Runs `python3 bin/skills-maintain`
4. Appends stdout/stderr to `landing/maintain.log`
5. Propagates the maintain exit code

## Schedule presets

| Use case | Flag |
|----------|------|
| Every 6 hours (default) | `--schedule '0 */6 * * *'` |
| Hourly | `--schedule '0 * * * *'` |
| Daily 3am | `--schedule '0 3 * * *'` |
| Every 15 min | `--schedule '*/15 * * * *'` |

## Prerequisites

Cron will not install dependencies. Before enabling:

```bash
pip3 install pyyaml
# or: pip3 install -e tools/skills-export
chmod +x bin/skills-maintain bin/skills-export scripts/cron/*.sh
```

Maintain updates files on disk only — it does **not** commit. Review with `git status` after runs.

## Files

| Path | Role |
|------|------|
| `config.env.example` | Documented defaults |
| `config.env` | Local overrides (gitignored; written by install) |
| `skills-maintain.sh` | Cron wrapper (PATH, logging, exit codes) |
| `install.sh` | Configure basics + install crontab |
| `uninstall.sh` | Remove marked crontab block |
