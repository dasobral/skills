# codebase-analysis skill

A Claude Code skill that analyses a codebase for coding style, patterns,
architecture, and standards, then persists the findings so that every
subsequent agent session automatically enforces those conventions.

---

## What it does

1. **Analyses** the full project (or a specified subset) across ten
   dimensions: architecture, code style, naming conventions,
   language/framework patterns, state management, error handling,
   testing, documentation, security, and developer workflow.

2. **Generates** a structured, actionable standards report using the
   template in `templates/report.md`.

3. **Writes** the report to `.claude/codebase-instructions.md` in the
   project root — a dedicated file managed exclusively by this skill.

4. **Wires** the instructions file into `CLAUDE.md` via an `@`-import
   so Claude Code loads the conventions automatically at every session
   start, with no extra setup required.

---

## File tree

```
codebase-analysis/
├── SKILL.md               # Skill definition and agent instructions
├── README.md              # This file
└── templates/
    └── report.md          # Report template filled in by the agent
```

---

## Installation

Copy (or symlink) the `codebase-analysis/` folder into your skills
directory:

```bash
# Project-level (recommended — checked in with the project)
cp -r codebase-analysis/ /path/to/your/project/.claude/skills/

# Personal (available in every project on this machine)
cp -r codebase-analysis/ ~/.claude/skills/
```

Claude Code discovers skills automatically — no restart needed.

---

## Usage

### Slash command (manual)

```
/codebase-analysis
```

### Automatic trigger

Claude will invoke the skill automatically when you phrase a request such
as:

- "Analyse the codebase and document the conventions."
- "Capture the coding standards of this project."
- "Extract the architecture patterns from `src/`."

### Scoped analysis

To restrict the analysis to a specific directory or file, include the
path in your prompt or add the file/folder to the context window:

```
/codebase-analysis   (then mention or attach src/api/)
Analyse only the frontend/ folder for code style.
```

---

## Output

After running, two files are created or updated in the project root:

| File | Purpose |
|------|---------|
| `.claude/codebase-instructions.md` | Full standards report (skill-managed) |
| `CLAUDE.md` | Gains one `@.claude/codebase-instructions.md` import line |

`.claude/codebase-instructions.md` is **fully regenerated** each time the
skill runs; do not edit it manually.

`CLAUDE.md` is only touched to add the import line — all other content is
preserved.

---

## Refreshing the analysis

Re-run `/codebase-analysis` whenever:

- The project undergoes a significant architectural change.
- A new framework or library is adopted.
- Coding style rules are intentionally updated.

---

## Report template

The template at `templates/report.md` defines the structure of the
generated instructions file. You can customise section headings or add
project-specific sections directly in the template — changes take effect
on the next run of the skill.
