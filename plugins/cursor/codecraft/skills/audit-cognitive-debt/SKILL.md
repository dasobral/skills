---
name: audit-cognitive-debt
description: >
  Audits cognitive load across seven debt categories: dead code,
  over-engineering, duplication, abstraction quality, control flow, naming,
  and test debt. Writes COGNITIVE_DEBT.md. Complements review-quality.
  Part of Codecraft plugin. Use when asked to audit cognitive load,
  find dead code, or analyze complexity.
---

# Audit Cognitive Debt

Analyze **cognitive friction** — mental overhead when reading/modifying code.
Distinct from functional correctness (tests) and security (review-quality P4).

Primary output: **`COGNITIVE_DEBT.md`**. Conversation gets a brief digest only.

## Step 1 — Resolve Scope

Path argument → attached files → full project.

## Step 2 — Load References

- `references/debt-categories.md` — seven categories + per-language heuristics
- `references/judgment-guidelines.md` — when NOT to flag
- `references/shared-heuristics.md` — dedup with review-quality

## Step 3 — Scale Analysis

| LOC | Mode |
|-----|------|
| <500 | Exhaustive — read every file |
| 500–5000 | Structural + 20% deep sample |
| >5000 | Sampled — 3–5 files per top-level module |

## Step 4 — Seven Categories

| # | Category |
|---|----------|
| D1 | Dead code |
| D2 | Over-engineering (defer to review-quality P2 for severity) |
| D3 | Duplication |
| D4 | Abstraction quality |
| D5 | Control flow complexity |
| D6 | Naming (defer to review-quality P1) |
| D7 | Test debt (defer to review-quality P3) |

Per finding: category, severity (HIGH/MEDIUM/LOW), file:line, evidence,
cognitive cost, recommendation, confidence (CERTAIN/LIKELY/UNCERTAIN).

## Step 5 — Write Report

Use `templates/COGNITIVE_DEBT.md`. Output priority:
1. `.cursor/COGNITIVE_DEBT.md`
2. `docs/COGNITIVE_DEBT.md`
3. `COGNITIVE_DEBT.md` (root)

## Step 6 — Digest

```
✓ Cognitive debt analysis complete.
Report: <path>
HIGH: N | MEDIUM: N | LOW: N
Top 3 priorities: ...
```

## Rules

- Never modify source files
- Apply judgment guidelines — don't pathologize intentional design
- Flag uncertainty with [UNCERTAIN]
- Note "What's Working Well" patterns
