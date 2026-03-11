---
name: codebase-analysis
description: >
  Analyzes the codebase (or a specified subset) for coding style, patterns,
  architecture, and standards. Generates a structured report saved as
  CLAUDE.md so future agent sessions automatically follow the established
  conventions. TRIGGER when the user asks to "analyze the codebase",
  "document coding standards", "capture code style", or similar.
  ALSO TRIGGER via /codebase-analysis slash command.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Codebase Analysis Skill

You are performing a deep codebase analysis. Your goal is to produce a
**coding standards and architecture report** that will be persisted as
`CLAUDE.md` (or appended as a dedicated section when one already exists)
so every future agent session automatically uses these conventions as
hard requirements.

---

## Step 1 — Determine Scope

Check whether the user has indicated a specific file, folder, or subset:

- If an explicit path was provided, restrict the analysis to that subtree.
- If nothing was specified, analyse the **entire project** starting from
  the working directory.

Always print the resolved scope before proceeding:
> "Analysing scope: `<path or 'full project'>`"

---

## Step 2 — Discover the Project Layout

Use `Glob` with `**/*` (depth-limited to ~3 levels first for an overview)
and `Read` on top-level configuration files to understand:

| Area | Files to examine |
|------|-----------------|
| Entry points | `main.*`, `index.*`, `app.*`, `server.*` |
| Package / dependency manifest | `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `pom.xml`, `*.gemspec`, `requirements*.txt`, `Pipfile` |
| Build / task runners | `Makefile`, `Taskfile.*`, `justfile`, `*.sh` scripts in root |
| Linter / formatter config | `.eslintrc*`, `.prettierrc*`, `ruff.toml`, `.flake8`, `pyproject.toml [tool.ruff]`, `rustfmt.toml`, `.golangci.*`, `checkstyle.xml` |
| Type-checker config | `tsconfig*.json`, `mypy.ini`, `.pyright*` |
| Test runner config | `jest.config.*`, `vitest.config.*`, `pytest.ini`, `conftest.py`, `*.test.ts` samples |
| CI/CD | `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile` |
| Project docs / instructions | `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md` |

---

## Step 3 — Deep-Dive Analysis

Work through each dimension below. For each, read representative samples
(at least 3–5 files per category, preferring files from different modules
or layers) and record concrete, specific findings — avoid vague
observations.

### 3.1 Architectural Patterns

- Overall structure: monolith / monorepo / microservices / layered /
  feature-based / domain-driven?
- Primary directories and their responsibilities.
- Module / package boundaries and dependency flow (what depends on what).
- Dependency injection or service-locator patterns (if any).
- Separation of concerns: where business logic, data access, and
  presentation live.
- Public API contracts: REST, GraphQL, RPC, event-driven?

### 3.2 Code Style & Formatting

- Indentation: tabs vs. spaces, size (2 / 4 / 8?).
- Quote style: single, double, backtick?
- Line length limit.
- Trailing commas, semicolons, braces style.
- File encoding and line endings (LF vs CRLF).
- Blank-line conventions (between functions, classes, sections).
- Import ordering and grouping rules.

### 3.3 Naming Conventions

- Variables / constants: camelCase, snake_case, UPPER_SNAKE, PascalCase?
- Functions / methods naming style and verb conventions.
- Classes / types / interfaces / enums naming style.
- File and directory naming style.
- Test file naming (`*.test.ts`, `test_*.py`, `*_spec.rb`…).
- Private / internal prefix or suffix conventions (`_`, `__`, `I`, `T`…).

### 3.4 Language & Framework Patterns

- Language version and notable features in active use.
- Framework(s) in use and version(s).
- Idiomatic patterns used (hooks, decorators, middleware, generics,
  iterators, async/await, goroutines, etc.).
- Patterns explicitly **avoided** or superseded in this codebase.
- Third-party library preferences (e.g. lodash vs. native, axios vs.
  fetch, SQLAlchemy vs. raw SQL).

### 3.5 State & Data Management

- How application state is managed (Redux, Zustand, Context API,
  MobX, Pinia, Signals…).
- Data-fetching patterns (SWR, React Query, REST hooks, repository
  pattern, ORMs…).
- DTO / schema / validation layer conventions (Zod, Pydantic, class-validator…).

### 3.6 Error Handling & Logging

- Error propagation style: exceptions, Result/Either types, error codes?
- Custom error classes or error enums defined.
- Logging library and log-level conventions.
- How errors surface to users (HTTP status codes, error payloads).

### 3.7 Testing Patterns

- Test pyramid balance (unit / integration / e2e).
- Test file co-location vs. separate `tests/` directory.
- Assertion library and matcher style.
- Fixture / factory / mock patterns.
- Coverage thresholds (if configured).
- Required tests for PRs (noted in CI).

### 3.8 Documentation & Comments

- JSDoc / docstring convention (all public APIs? none? selected?).
- Inline comment style (full sentences? fragment? `//` vs `#`?).
- `TODO`, `FIXME`, `HACK` conventions.
- API documentation tools (Swagger/OpenAPI, typedoc, sphinx…).

### 3.9 Security & Performance Conventions

- Input validation boundaries.
- Auth / authz pattern.
- Secret management approach (env vars, vault references…).
- Any noted performance patterns (memoization, pagination defaults,
  caching layers).

### 3.10 Developer Workflow

- How to install dependencies.
- How to run, build, lint, format, and test locally.
- Pre-commit hooks or CI gates that enforce quality.
- Branch / commit message conventions (if visible in git history or docs).

---

## Step 4 — Synthesize the Report

Compose a structured Markdown report using the template below. Fill every
section with **specific, actionable rules** — not summaries of what you
observed. Write each rule as an imperative sentence a developer can
follow directly. For sections where the codebase has no established
pattern, write `No established pattern — prefer [reasonable default]`.

```markdown
# Codebase Standards & Architecture Guide

> Auto-generated by the `codebase-analysis` skill on {ISO date}.
> Update this file whenever a pattern is intentionally changed.

## Project Overview
<!-- 2–4 sentences: what the project does, its primary tech stack, and
     the top-level directory map. -->

## Architecture

### Structure
<!-- Bullet list of top-level directories and their purpose. -->

### Dependency Flow
<!-- Describe allowed and forbidden dependency directions. -->

### Key Patterns
<!-- e.g. "Use repository pattern for all DB access. Controllers must
     not contain business logic." -->

## Code Style

| Rule | Value |
|------|-------|
| Indentation | … |
| Quotes | … |
| Line length | … |
| Semicolons | … |
| Trailing commas | … |
| Line endings | … |

## Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Variables | … | … |
| Constants | … | … |
| Functions | … | … |
| Classes / Types | … | … |
| Files | … | … |
| Directories | … | … |
| Tests | … | … |

## Language & Framework Rules

- **Language version**: …
- **Framework**: …
- Preferred patterns (with brief rationale):
  - …
- Patterns to avoid:
  - …

## State & Data Management

- …

## Error Handling & Logging

- …

## Testing Requirements

- …

## Documentation & Comments

- …

## Security & Performance

- …

## Developer Workflow

```bash
# Install
…
# Run
…
# Lint / format
…
# Test
…
```

## What NOT To Do

<!-- Common anti-patterns seen in this codebase or explicitly
     prohibited by the project. -->

---
*Keep this file in sync with the codebase. Run `/codebase-analysis` again
after significant architectural changes.*
```

---

## Step 5 — Persist the Report

### Case A — No `CLAUDE.md` exists yet

Write the complete report to `CLAUDE.md` in the **project root** (or
the root of the analysed subtree if a subset was requested).

### Case B — `CLAUDE.md` already exists

1. Read the existing file.
2. If a `# Codebase Standards & Architecture Guide` section already
   exists, **replace only that section** (from its heading to the next
   `---` or `#` at the same depth).
3. If no such section exists, **append** the full report at the end,
   preceded by a horizontal rule `---`.
4. Preserve all other content in the file unchanged.

After writing, confirm with the user:
> "Analysis complete. Standards saved to `CLAUDE.md`.
> Future Claude Code sessions will load these conventions automatically."

---

## Important Rules for This Skill

- Be **specific and concrete** — avoid sentences like "the code is
  well-structured". Write rules a developer can apply.
- Prefer **reading real files** over inferring from filenames alone.
  Spot-check at least one file per layer/module.
- If the codebase is large, prioritise breadth (one sample per
  category) over depth in any single file.
- Do **not** modify any source files. Only write to `CLAUDE.md`.
- When patterns conflict between files (e.g. mixed quote styles),
  document the dominant pattern and flag the inconsistency explicitly
  under "What NOT To Do".
