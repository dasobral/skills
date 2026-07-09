# Codex adapter

Codex bundles are **generated** by `skills-export export codex`.

Each bundle includes:
- `.agents/skills/<skill>/` — portable core skills (Codex discovery path)
- `.agents/instructions.md` — convention pointer
- `AGENTS.md` — imports instructions
- `bundle.json` — install metadata

Flat export (`dist/codex/skills/`) installs to `~/.codex/skills/` or `~/.agents/skills/`.
