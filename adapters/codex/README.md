# Codex adapters

This directory contains the Codex-specific authoring overlays for native
plugins. Portable skills and shared metadata remain under `core/`; generated
native plugins are written under `plugins/codex/`.

The six cross-platform families (`codecraft`, `cpp-qkd-toolkit`,
`agent-platform`, `aos-stack`, `scientific-computing`, and `career-writer`)
also have Cursor output. The five workflow families (`agentic-trust-gate`,
`agent-attack-replay`, `crypto-change-radar`, `entropy-flight-recorder`, and
`scientific-claim-ledger`) are Codex-only.

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

Add portable skill names and plugin metadata to `core/manifest.yaml`, keep
portable instructions under `core/skills/`, and put only Codex-specific files
in an overlay. Regenerate with:

```bash
./bin/skills-export sync codex
./bin/skills-export validate codex
```

Do not edit `plugins/codex/` or `.agents/plugins/marketplace.json` directly.

Agent templates are bundled but are not installed automatically. Plugins with
agents receive the shared `install-plugin-agents` skill, which previews and
installs them into project or user `.codex/agents/` only after confirmation.
The native plugin installer likewise copies plugins and marketplace metadata
without installing agents. Start a new Codex session after agent installation.

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

Review and trust every bundled hook and referenced script before enabling it.
Hooks receive project context on standard input, emit Codex hook output, use
bounded timeouts, and must not write project files. Static validation checks
shape, references, and path containment; it does not establish that hook logic
is trustworthy.

The workflow overlays define evidence contracts, deterministic checks, agent
authority, data handling, and explicit limitations in their READMEs. They do
not certify safety, cryptographic or entropy adequacy, standards compliance, or
scientific validity. Missing evidence and unavailable optional tooling remain
visible `evidence-gap` states; authorization and expert decisions stay with the
user.
