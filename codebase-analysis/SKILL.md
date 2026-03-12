---
name: codebase-analysis
description: >
  Analyzes the codebase (or a specified subset) for coding style, patterns,
  architecture, and standards. Persists the findings to
  `.claude/codebase-instructions.md` and wires it into `CLAUDE.md` via an
  @-import so every subsequent agent session loads the conventions
  automatically as hard coding requirements.
  TRIGGER when the user asks to "analyze the codebase", "document coding
  standards", "capture code style", "extract conventions", or similar.
  ALSO TRIGGER via /codebase-analysis slash command.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Codebase Analysis Skill

Perform a structured analysis of the codebase and persist the findings so
that **every future agent session inherits the established conventions
automatically**, without the user needing to repeat them.

Output is written to **`.claude/codebase-instructions.md`** — a dedicated,
skill-managed file that keeps generated content separate from hand-written
project notes. `CLAUDE.md` is updated with a single `@`-import line so
Claude Code loads the instructions file at session start.

---

## Step 1 — Resolve Scope

Determine what to analyse:

- If the user's message references a specific path, file, or folder
  (including files added to context), restrict the analysis to that subtree.
- Otherwise, analyse the **entire project** starting from the working
  directory.

Announce the resolved scope before continuing:
> "Analysing scope: `<resolved path or 'full project'>`"

---

## Step 2 — Load the Report Template

Read the template file located at:

```
<skill_base_path>/templates/report.md
```

You will fill this template with concrete findings in Step 4.
Replace `{{ISO_DATE}}` with today's date and `{{ANALYSIS_SCOPE}}` with the
resolved scope from Step 1.

---

## Step 3 — Discover the Project Layout

Glob the project tree (limit to 3 levels deep for the first pass), then
read the most relevant configuration and entry-point files:

| Area | Files to examine |
|------|-----------------|
| Entry points | `main.*`, `index.*`, `app.*`, `server.*`, `cmd/*/main.*` |
| Dependency manifests | `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `pom.xml`, `build.gradle*`, `*.gemspec`, `requirements*.txt`, `Pipfile` |
| Build / task runners | `Makefile`, `Taskfile.*`, `justfile`, root `*.sh` scripts |
| Linter / formatter | `.eslintrc*`, `.prettierrc*`, `ruff.toml`, `.flake8`, `rustfmt.toml`, `.golangci.*`, `checkstyle.xml`, `biome.json` |
| Type checker | `tsconfig*.json`, `mypy.ini`, `pyrightconfig.json` |
| Test runner | `jest.config.*`, `vitest.config.*`, `pytest.ini`, `conftest.py` |
| CI/CD | `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml` |
| Existing instructions | `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md`, `.claude/codebase-instructions.md` |

Read the existing `.claude/codebase-instructions.md` if it exists — note
which sections are already accurate so you can preserve or update them.

---

## Step 4 — Deep-Dive Analysis

For each dimension below, read **3–5 representative source files** spread
across different modules or layers. Prefer reading real code over inferring
from filenames alone. Record **specific, actionable findings** — avoid
vague observations like "the code is well-structured".

Work through all ten dimensions even if some feel short; write
`No established pattern — prefer [reasonable default]` when nothing is found.

### 4.1 Architectural Patterns

- Overall structure: monolith / monorepo / microservices / layered /
  feature-based / domain-driven / hexagonal?
- Primary directories and their single responsibility.
- Module / package boundaries and dependency flow (what may import what).
- Dependency injection, service-locator, or factory patterns.
- Where business logic, data access, and presentation live.
- Public API contracts: REST, GraphQL, RPC, events, CLI?

### 4.2 Code Style & Formatting

- Indentation: tabs vs. spaces, width.
- Quote style (single / double / backtick).
- Max line length.
- Trailing commas, semicolons, brace style.
- File encoding and line endings (LF vs. CRLF).
- Blank-line conventions (between functions, classes, top-level blocks).
- Import ordering and grouping rules.

### 4.3 Naming Conventions

- Variables and constants.
- Functions and methods (verb conventions, boolean prefixes like `is`, `has`).
- Classes, structs, interfaces, enums, type aliases.
- Files and directories.
- Test files and test helpers.
- Private / internal indicators (`_`, `__`, `I` prefix, etc.).

### 4.4 Language & Framework Patterns

- Language version and features actively used.
- Framework(s) and version(s).
- Idiomatic patterns in use (hooks, decorators, middleware, async/await, etc.).
- Patterns explicitly avoided or superseded.
- Preferred third-party libraries (e.g. `date-fns` not `moment`, `zod` not `joi`).

### 4.5 State & Data Management

- Application state management (Redux, Zustand, Pinia, Context, Signals, etc.).
- Data-fetching (SWR, React Query, REST hooks, repository pattern, ORMs).
- DTO / schema / validation layer (Zod, Pydantic, class-validator, etc.).

### 4.6 Error Handling & Logging

- Error propagation: exceptions, Result/Either types, or error codes?
- Custom error classes or error enums.
- Logging library and log-level conventions.
- How errors surface to users (HTTP status codes, payload shape).

### 4.7 Testing Patterns

- Test pyramid balance (unit / integration / e2e).
- Test file co-location vs. separate `tests/` directory.
- Assertion library and matcher style.
- Fixture / factory / mock patterns.
- Coverage thresholds enforced by CI.

### 4.8 Documentation & Comments

- Docstring / JSDoc convention (all public APIs / complex logic only / none).
- Inline comment style.
- `TODO`, `FIXME`, `HACK` conventions (with ticket references?).
- API documentation tools (OpenAPI, TypeDoc, Sphinx, etc.).

### 4.9 Security & Performance Conventions

- Input validation boundary.
- Auth / authz pattern.
- Secret management (env vars, vault, etc.).
- Noted performance patterns (memoisation, pagination defaults, caching).

### 4.10 Developer Workflow

- Install, run, lint, format, type-check, test, and build commands.
- Pre-commit hooks or CI gates.
- Branch naming and commit message conventions.

---

## Step 5 — Write `.claude/codebase-instructions.md`

Using the template loaded in Step 2, fill every section with the findings
from Step 4. Rules:

- Write each entry as an **imperative sentence** a developer can follow.
- Be specific: "Use 2-space indentation" not "indentation is consistent".
- When patterns conflict across files, document the dominant one and list
  the deviation under **What NOT To Do**.
- Do **not** touch any source file — only write the instructions file.

Determine the target path:

- If the analysis scope is the full project or a path inside the project
  root: write to `{project_root}/.claude/codebase-instructions.md`.
- If the scope is a specific subtree: write to
  `{subtree_root}/.claude/codebase-instructions.md`.

Create the `.claude/` directory if it does not exist.

If `.claude/codebase-instructions.md` **already exists**, refresh it
entirely — the template is the canonical structure. Do not preserve
old free-form content; the new analysis supersedes it.

---

## Step 6 — Wire into `CLAUDE.md`

Ensure Claude Code loads the instructions file automatically at every
session start by adding an `@`-import to `CLAUDE.md`.

The import line to add:

```
@.claude/codebase-instructions.md
```

### Case A — `CLAUDE.md` does not exist

Create it with exactly this content:

```markdown
@.claude/codebase-instructions.md
```

### Case B — `CLAUDE.md` exists and already contains the import

Do nothing. The file is already wired correctly.

### Case C — `CLAUDE.md` exists but does not contain the import

Prepend the import line at the very top of the file, followed by a blank
line, leaving all other content unchanged:

```
@.claude/codebase-instructions.md

<existing content>
```

---

## Step 7 — Confirm

Print a summary message:

```
✓ Analysis complete.

Standards written to : .claude/codebase-instructions.md
Auto-loaded via      : CLAUDE.md (@-import)

Every future Claude Code session in this project will load these
conventions automatically. Re-run /codebase-analysis after significant
architectural changes.
```

---

## Skill Rules

- Read real files — do not infer patterns from filenames alone.
- Prioritise **breadth** (one sample per category) over depth in any
  single file when the codebase is large.
- Never modify source files. Only write `.claude/codebase-instructions.md`
  and (minimally) `CLAUDE.md`.
- Produce **rules**, not observations. Every sentence in the output file
  must be actionable by a developer writing new code.
