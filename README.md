# skills

A collection of Claude Code skills for coding agents. Each skill is a
self-contained directory that can be cloned and dropped into any project's
`.claude/skills/` folder (or `~/.claude/skills/` for personal use).

---

## Installation

```bash
# Clone the repo
git clone <repo-url> skills

# Copy a skill into your project
cp -r skills/<skill-name> /path/to/your/project/.claude/skills/

# Or install personally (available in all projects)
cp -r skills/<skill-name> ~/.claude/skills/
```

Claude Code picks up new skills automatically — no restart needed.

---

## Skills

### [analyze-codebase](./codebase-analysis/)

Analyses a codebase across 16 dimensions — architecture, naming,
formatting, async patterns, error handling, testing, anti-patterns, and
more — then writes a prescriptive `CODING_REQUIREMENTS.md` that future
agent sessions load automatically as hard coding rules.

**Slash command**: `/analyze-codebase [path]`

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and step-by-step agent instructions |
| `templates/report.md` | Output template with 16 sections |
| `references/analysis-dimensions.md` | Full 16-dimension analysis checklist |

---

## Skill structure

Every skill in this repo follows the standard Claude Code layout:

```
<skill-name>/
├── SKILL.md                 # Required — frontmatter + agent instructions
├── README.md                # Usage documentation
└── <supporting files>/      # Templates, references, scripts as needed
```

The `name` field in `SKILL.md` frontmatter becomes the `/slash-command`.
