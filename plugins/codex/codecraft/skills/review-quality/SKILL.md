---
name: review-quality
description: >
  Language-agnostic code review across four pillars: Clarity, Simplicity,
  Good Practices, and Security. Produces severity-tagged findings
  (CRITICAL/WARNING/SUGGESTION). Complements audit-cognitive-debt for
  dead code and duplication. Part of Codecraft plugin.
  Use when asked to review code quality, audit security, check best
  practices, or find code smells.
---

# Review Quality

Structured, severity-tagged review across **four pillars**. Focus on code
health and maintainability — not functional correctness (that's for tests).

## Step 1 — Resolve Scope

1. Path argument
2. Attached/mentioned files
3. Pasted code block
4. Working directory glob for source extensions (exclude build/vendor dirs)

Announce: `Reviewing scope: <path>`

## Step 2 — Load Checklist

Read `references/review-checklist.md` and `references/shared-heuristics.md`.

## Step 3 — Analyze (Four Pillars)

| Pillar | Focus |
|--------|-------|
| P1 Clarity | Naming, structure, readability |
| P2 Simplicity | Complexity, over-engineering, YAGNI |
| P3 Good Practices | SOLID, DRY, error handling, testability |
| P4 Security | Injection, secrets, deserialization, deps |

Per finding: severity, pillar tag, file:line, problem, consequence, fix snippet.

Severity rules:
- **CRITICAL** — security vulnerability or production defect
- **WARNING** — significant maintainability/reliability issue
- **SUGGESTION** — minor improvement

## Step 4 — Report

Use `templates/review-report.md`. Output to conversation (not a file unless asked).

Include health summary table and rating: CRITICAL / NEEDS WORK / HEALTHY / EXCELLENT.

## Step 5 — Delegate for Large Scopes

For >5 files or >2000 LOC, run parallel module reviewers (one per module), then
synthesize. See `references/platform-orchestration.md` for platform-specific
parallel worker mechanisms.

## Rules

- Real issues only; quote bad code with file:line
- Every CRITICAL/WARNING needs a fix snippet
- Read-only — never modify source unless asked
- For cognitive friction (dead code, duplication), suggest `audit-cognitive-debt`
