---
name: write-conformant-code
description: >
  Write code in any language that matches project conventions exactly. Reads
  CODING_REQUIREMENTS.md, prior review output, or built-in defaults before
  writing. Part of Codecraft pipeline: analyze → write → review → audit.
  Use when implementing features, functions, or any code that should fit
  seamlessly into an existing codebase.
---

# Write Conformant Code

Write code that belongs in the codebase — every line should look like it was
written by a senior engineer already on the team.

## Pipeline Position

```
analyze-codebase → write-conformant-code → review-quality → audit-cognitive-debt
```

## Step 1 — Load Style Context

| Priority | Source |
|----------|--------|
| 1 | `CODING_REQUIREMENTS.md` (`.cursor/`, `docs/`, or root) |
| 2 | `review-quality` output in current conversation |
| 3 | User-provided style notes |
| 4 | `references/default-style.md` for detected language |

Announce which source was used. If no requirements file exists:
> No CODING_REQUIREMENTS.md found — using defaults. Run analyze-codebase first.

## Step 2 — Read Before Writing

Glob and read 2–3 files in the target module. Match:
- Naming (functions, types, files)
- Error handling patterns
- Import/module structure
- Test placement and style
- Comment density

## Step 3 — Plan the Change

State: files to create/modify, public API surface, error cases, test approach.
Keep scope minimal — only what the user asked for.

## Step 4 — Implement

Output code-first. For each file:
- Full implementation (not stubs)
- Imports matching project style
- Tests when the project has a test culture

See `references/task-patterns.md` for common task shapes.

## Step 5 — Self-Check

Before finishing, verify against loaded conventions:
- [ ] Naming matches surrounding code
- [ ] Error handling follows project pattern
- [ ] No unnecessary abstractions
- [ ] Tests included if project tests similar code

Suggest running `review-quality` on the diff.

## Rules

- Never invent conventions — infer from code or requirements file
- Minimize diff scope
- See `references/pipeline-integration.md` for full pipeline usage
