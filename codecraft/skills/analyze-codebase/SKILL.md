---
name: analyze-codebase
description: >
  Analyzes a codebase across 16 dimensions — naming, formatting, architecture,
  async patterns, error handling, testing, anti-patterns — and writes
  CODING_REQUIREMENTS.md as prescriptive rules for future agent sessions.
  Part of the Codecraft plugin pipeline: analyze → write → review → audit.
  Use when asked to analyze conventions, document coding standards, capture
  code style, or extract project patterns.
---

# Analyze Codebase

Perform structured analysis and persist findings as **`CODING_REQUIREMENTS.md`**
— prescriptive, imperative requirements future agents must follow.

Write rules as actionable imperatives with concrete examples from the codebase
(`Use Result<T, E> for fallible ops — see src/db/query.rs`), not observations.

## Step 1 — Resolve Scope

1. Path argument if provided
2. Attached or mentioned files/folders
3. Full project (default)

Announce: `Analysing scope: <path>`

## Step 2 — Load Checklist

Read `references/analysis-dimensions.md` and keep in context.

## Step 3 — Discover Layout

Glob 3 levels deep (exclude `node_modules`, `.git`, `target`, `build`, `dist`).
Read entry points, manifests, linters, test config, CI, and existing instructions
(`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `CODING_REQUIREMENTS.md`).

## Step 4 — Deep-Dive (16 Dimensions)

For each dimension, read 3–5 representative files across modules. Capture:
- Imperative rule
- File:line example
- Anti-patterns to avoid

## Step 5 — Write Output

Use `templates/report.md`. Output location priority:
1. `.cursor/CODING_REQUIREMENTS.md`
2. `docs/CODING_REQUIREMENTS.md`
3. `CODING_REQUIREMENTS.md` (root)

## Step 6 — Wire Agent Instructions

Create or update pointer files so conventions auto-load:

**`.cursor/instructions.md`** (create if missing):
```markdown
# Agent Instructions
Before writing code, read: @<relative-path-to-CODING_REQUIREMENTS.md>
These requirements are authoritative.
```

**`AGENTS.md`** — prepend if missing:
```
@.cursor/instructions.md
```

## Step 7 — Confirm

```
✓ Analysis complete.
Requirements: <path>
Pointer: .cursor/instructions.md
Re-run after significant architectural changes.
```

## Rules

- Prescriptive imperatives only; cite real code
- Read files, don't infer from names
- Never modify source files — only requirements and pointer files
- Pair with `write-conformant-code` skill for implementation
