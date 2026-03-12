---
name: analyze-codebase
description: >
  Analyzes the codebase (or a specified subset) across 16 dimensions —
  naming, formatting, architecture, async patterns, error handling, testing,
  anti-patterns, and more — then writes CODING_REQUIREMENTS.md in a
  prescriptive, imperative format so future agents treat it as hard coding
  requirements. Also writes .claude/instructions.md as an agent-agnostic
  pointer to that file.
  TRIGGER when the user asks to "analyze the codebase", "document coding
  standards", "capture conventions", "extract code style", or similar.
  ALSO TRIGGER via /analyze-codebase slash command.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Codebase Analysis Skill

Perform a structured analysis of the codebase and persist the findings as
**`CODING_REQUIREMENTS.md`** — a prescriptive, imperative requirements file
that future agents must follow when writing or modifying code in this project.

Write rules as actionable imperatives with concrete examples pulled from the
actual codebase ("Use `Result<T, E>` for all fallible operations — see
`src/db/query.rs`"), not observations ("the codebase uses Result").

---

## Step 1 — Resolve Scope

Determine what to analyse from, in order of precedence:

1. **Inline path argument** — if the slash command was invoked as
   `/analyze-codebase <path>`, use that path.
2. **Context files** — if the user attached or mentioned specific files or
   folders, restrict analysis to those.
3. **Full project** — default when no path is specified.

Announce the resolved scope before continuing:
> "Analysing scope: `<resolved path or 'full project'>`"

---

## Step 2 — Load the Analysis Checklist

Read the full dimension checklist from:

```
<skill_base_path>/references/analysis-dimensions.md
```

Keep it in context throughout the analysis — it defines exactly what to
look for in each of the 16 dimensions.

---

## Step 3 — Discover the Project Layout

Glob the project tree to 3 levels deep for an overview, excluding noise:
`node_modules`, `.git`, `target`, `__pycache__`, `dist`, `build`, `.next`,
`vendor`, lock files (`*.lock`, `package-lock.json`, `yarn.lock`).

Then read the most relevant configuration and entry-point files:

| Area | Files to examine |
|------|-----------------|
| Entry points | `main.*`, `index.*`, `app.*`, `server.*`, `cmd/*/main.*` |
| Dependency manifests | `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `pom.xml`, `build.gradle*`, `requirements*.txt`, `Pipfile` |
| Linter / formatter | `.eslintrc*`, `.prettierrc*`, `ruff.toml`, `.flake8`, `rustfmt.toml`, `.golangci.*`, `biome.json` |
| Type checker | `tsconfig*.json`, `mypy.ini`, `pyrightconfig.json` |
| Test runner | `jest.config.*`, `vitest.config.*`, `pytest.ini`, `conftest.py` |
| Build / task runners | `Makefile`, `Taskfile.*`, `justfile`, root `*.sh` scripts |
| CI/CD | `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile` |
| Existing instructions | `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md`, `.claude/instructions.md`, `CODING_REQUIREMENTS.md`, `docs/CODING_REQUIREMENTS.md`, `.claude/CODING_REQUIREMENTS.md` |

If a previous `CODING_REQUIREMENTS.md` exists in any location, read it and
note which sections can be preserved vs. refreshed.

---

## Step 4 — Deep-Dive Analysis

For each of the 16 dimensions in the checklist (loaded in Step 2), read
**3–5 representative source files** spread across different modules or
layers. Prefer real code over filenames alone.

For every finding, capture:
- The concrete rule to follow (imperative form).
- At least one real file path + line reference as an example.
- Any counter-examples or inconsistencies to flag as anti-patterns.

Do not skip dimensions. Write `No established pattern — prefer
[reasonable default]` for dimensions with no evidence.

---

## Step 5 — Load the Report Template

Read the output template from:

```
<skill_base_path>/templates/report.md
```

Replace `{{ISO_DATE}}` with today's date and `{{ANALYSIS_SCOPE}}` with
the scope from Step 1. Then fill every section with the findings from
Step 4, following the writing rules in the template header.

---

## Step 6 — Choose the Output Location

Pick the first location that exists or can be created, in this priority order:

| Priority | Path | Use when |
|----------|------|----------|
| 1 | `.claude/CODING_REQUIREMENTS.md` | `.claude/` directory already exists |
| 2 | `docs/CODING_REQUIREMENTS.md` | `docs/` directory already exists |
| 3 | `CODING_REQUIREMENTS.md` | fallback — write to project root |

Create the target directory if needed. If a `CODING_REQUIREMENTS.md`
already exists at the chosen location, overwrite it entirely — the new
analysis supersedes the old one.

Remember the final path; you will need it in Step 7.

---

## Step 7 — Write the Pointer File

Create `.claude/instructions.md` in the project root with the following
content (adjust the relative path to match the location chosen in Step 6):

```markdown
# Agent Instructions

Before writing or modifying any code in this project, read the coding
requirements file:

@<relative path to CODING_REQUIREMENTS.md>

These requirements are authoritative. Follow them in every change,
regardless of personal style preferences or general best practices that
conflict with what is documented there.
```

If `.claude/instructions.md` already exists, replace only the
`@<path>` line — preserve any other content the user has written.

---

## Step 8 — Wire into CLAUDE.md

Ensure Claude Code auto-loads the instructions at every session start.

The import line to add:

```
@.claude/instructions.md
```

**Case A** — `CLAUDE.md` does not exist: create it containing only that line.

**Case B** — `CLAUDE.md` exists and already contains `@.claude/instructions.md`:
do nothing.

**Case C** — `CLAUDE.md` exists but is missing the import: prepend the
import line at the very top, followed by a blank line, leaving all other
content intact.

---

## Step 9 — Confirm

Print a concise summary:

```
✓ Analysis complete.

Requirements written to : <chosen path from Step 6>
Agent pointer           : .claude/instructions.md
Auto-loaded via         : CLAUDE.md  (@.claude/instructions.md)

Every future Claude Code session will load these requirements automatically.
Re-run /analyze-codebase [path] after significant architectural changes.
```

---

## Skill Rules

- **Prescriptive, not descriptive.** Every sentence in the output file must
  be an actionable imperative. "Use 2-space indentation" not "indentation
  is 2 spaces".
- **Cite real code.** Embed file paths and line references for every rule
  so developers and agents can verify them.
- **Anti-patterns matter.** What not to do is as important as what to do.
  Explicitly list deviations and forbidden patterns observed in the code.
- **Read, don't infer.** Always open files to confirm patterns rather than
  guessing from filenames or directory structure.
- **Breadth over depth** when the codebase is large — one solid sample per
  dimension beats exhaustive coverage of one module.
- **Never modify source files.** Only write `CODING_REQUIREMENTS.md`,
  `.claude/instructions.md`, and (minimally) `CLAUDE.md`.
