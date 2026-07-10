# Plugins

Platform-ready plugin trees generated from `core/` + `adapters/`.

| Path | Status |
|------|--------|
| [`cursor/`](./cursor/) | **Generated and committed** — 6 native Cursor plugins |
| [`codex/`](./codex/) | **Generated and committed** — 11 native Codex plugins |
| `dist/claude/skills/` | Generated, uncommitted flat Claude skills |
| `dist/codex/skills/` | Generated, uncommitted flat Codex skills |

Regenerate native plugins and marketplaces:

```bash
./bin/skills-export sync cursor
./bin/skills-export sync codex
./bin/skills-export validate
```

Cursor discovery uses `.cursor-plugin/marketplace.json`; Codex discovery uses
`.agents/plugins/marketplace.json`. Author portable content in `core/` and
platform overlays in `adapters/`; never edit generated plugin trees directly.

Native Codex hooks are executable code and require an explicit trust review.
Bundled Codex agent TOML files are templates, not automatic configuration; use
the generated `install-plugin-agents` skill to preview and explicitly install
them into project or user `.codex/agents/`.

The five Codex-only workflow plugins produce bounded evidence for repository
trust, agent attack replay, cryptographic change, entropy qualification, and
scientific claims. Their records expose missing evidence and do not certify
safety, compliance, entropy/cryptographic adequacy, or scientific validity.
