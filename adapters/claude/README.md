# Claude Code adapter

Claude bundles are **generated** by `skills-export export claude`.

Each bundle includes:
- `.claude/skills/<skill>/` — portable core skills
- `.claude/instructions.md` — convention pointer
- `CLAUDE.md` — imports instructions
- `bundle.json` — install metadata

Flat export (`dist/claude/skills/`) installs to `~/.claude/skills/`.
