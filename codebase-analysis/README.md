# analyze-codebase skill

Analyses a codebase across 16 dimensions and writes a prescriptive
`CODING_REQUIREMENTS.md` that future agents load automatically as hard
coding rules.

---

## What it does

1. **Analyses** the full project (or a specified path) using the 16-dimension
   checklist in `references/analysis-dimensions.md`.

2. **Writes** `CODING_REQUIREMENTS.md` in the most discoverable location:
   `.claude/` → `docs/` → project root (first directory that exists).

3. **Writes** `.claude/instructions.md` — an agent-agnostic pointer file
   that tells any agent to read `CODING_REQUIREMENTS.md` before touching code.

4. **Wires** `CLAUDE.md` with `@.claude/instructions.md` so Claude Code
   loads everything automatically at session start.

The output is **prescriptive**, not descriptive. Rules read as imperatives
("Use `Result<T,E>` for all fallible operations") and are backed by real
file references from the codebase.

---

## File tree

```
codebase-analysis/
├── SKILL.md                           # Skill definition and agent instructions
├── README.md                          # This file
├── templates/
│   └── report.md                      # Output template (16 sections)
└── references/
    └── analysis-dimensions.md         # Full 16-dimension analysis checklist
```

---

## Installation

Copy the `codebase-analysis/` folder into your skills directory:

```bash
# Project-level (checked in with the project — recommended)
cp -r codebase-analysis/ /path/to/project/.claude/skills/

# Personal (available across all projects on this machine)
cp -r codebase-analysis/ ~/.claude/skills/
```

Claude Code discovers skills automatically on the next session start.

---

## Usage

### Slash command

```
/analyze-codebase              # analyse the full project
/analyze-codebase src/api/     # analyse a specific path
/analyze-codebase src/auth.ts  # analyse a single file
```

### Natural language triggers

Claude invokes the skill automatically when you write phrases like:

- "Analyse the codebase and document the conventions."
- "Capture the coding standards for this project."
- "Extract the architecture and style rules from `src/`."
- "Document what patterns I should follow when adding code here."

### Scoped analysis

Provide a path inline with the slash command, or attach / mention specific
files and folders in your message — the skill restricts its analysis to
that scope.

---

## Output files (written to the target project)

| File | Purpose | Managed by |
|------|---------|------------|
| `.claude/CODING_REQUIREMENTS.md` *(or `docs/` or root)* | Full standards report | Skill — overwritten on each run |
| `.claude/instructions.md` | Agent-agnostic pointer to requirements | Skill — `@path` line updated on each run |
| `CLAUDE.md` | Gains one `@.claude/instructions.md` import | Skill — only the import line is touched |

---

## Auto-loading chain

```
CLAUDE.md
  └─ @.claude/instructions.md          ← pointer file
       └─ @.claude/CODING_REQUIREMENTS.md   ← actual rules
```

Every Claude Code session reads this chain automatically. Other agents
(Codex CLI, custom agents) can read `.claude/instructions.md` directly.

---

## When to refresh

Re-run `/analyze-codebase` after:

- A significant architectural change.
- Adopting a new framework, library, or language feature.
- Intentionally changing a style or naming convention.

The `CODING_REQUIREMENTS.md` is fully regenerated each time. The pointer
file and `CLAUDE.md` import are updated minimally (only the `@path` line).

---

## Customising the report structure

Edit `templates/report.md` to add, remove, or rename sections. Changes
take effect on the next run. The 16-dimension checklist in
`references/analysis-dimensions.md` controls what the agent looks for
during the analysis phase — edit it to focus on dimensions relevant to
your stack.
