# Codex adapters

This directory contains the Codex-specific authoring overlays for native
plugins. Portable skills and shared metadata remain under `core/`; generated
native plugins are written under `plugins/codex/`.

## Overlay layout

An adapter may provide:

- `.codex-plugin/plugin.json` — Codex presentation metadata merged with the
  core plugin manifest;
- `agents/*.toml` — optional project/user agent templates;
- `hooks/hooks.json` and `hooks/scripts/` — optional native Codex lifecycle
  hooks using `${PLUGIN_ROOT}`;
- `README.md` — operational workflow, inputs, artifacts, authority, guarantees,
  and limitations copied into generated output;
- `skills/` and safe assets — Codex-only additions.

Agent templates are bundled but are not installed automatically. Plugins with
agents receive the shared `install-plugin-agents` skill, which previews and
installs them into project or user `.codex/agents/` only after confirmation.

## Generated native plugin

Each generated `plugins/codex/<plugin>/` contains:

- `.codex-plugin/plugin.json`;
- `skills/<skill>/`;
- optional `agents/*.toml`;
- optional `hooks/hooks.json` and bundled scripts;
- the adapter-authored `README.md` (with a generated fallback for incomplete
  third-party overlays).

The native marketplace is generated at `.agents/plugins/marketplace.json`.
Flat skill export remains a separate compatibility artifact at
`dist/codex/skills/`.

Review and trust every bundled hook before enabling it. Hooks receive project
context on standard input, emit the official Codex hook output schema, use
bounded timeouts, and must not write project files.
