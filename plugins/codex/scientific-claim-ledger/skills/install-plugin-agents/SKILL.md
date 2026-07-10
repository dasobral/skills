---
name: install-plugin-agents
description: Safely preview and install this plugin's bundled Codex agent templates.
---

# Install plugin agents

Use the bundled installer; never copy or overwrite agent files manually.

1. Ask the user to choose project or user scope.
2. Run `scripts/install_agents.py` with the chosen scope and `--dry-run`.
3. Show all reported additions and conflicts.
4. Obtain explicit confirmation before changing files.
5. Rerun the same command without `--dry-run`.
6. Report the result and tell the user to start a new Codex session.

For project scope, pass `--scope project --project-root <project-root>`.
For user scope, pass `--scope user --home <home-directory>`.
Stop without installing if the preview reports conflicts.
