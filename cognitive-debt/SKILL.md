---
name: cognitive-debt
description: >
  Analyses a codebase (or a specified subset) for accumulated cognitive load —
  the mental effort required to read, understand, and modify code. Identifies
  seven debt categories: dead code, over-engineering, duplication, abstraction
  quality, control flow complexity, naming, and test debt. Applies per-language
  heuristics for Python, TypeScript/JS, Rust, C++, and Go. Scales analysis
  depth to codebase size (exhaustive for <500 LOC, structural + sampled for
  larger codebases). Writes COGNITIVE_DEBT.md with a severity table, per-finding
  evidence, actionable recommendations, prioritized action list, and a
  "what's working well" section. Complements codebase-analyst (structure and
  dependencies) and code-quality-reviewer (correctness and security pillars) but
  focuses purely on cognitive friction.
  TRIGGER when the user asks to "audit cognitive load", "find cognitive debt",
  "identify over-engineering", "find dead code", "analyse complexity",
  "check abstraction quality", "find naming issues", or similar.
  ALSO TRIGGER via /cognitive-debt slash command.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Cognitive Debt Skill

Analyse the codebase for **cognitive debt** — the accumulated mental overhead
that makes code harder to read, understand, and safely modify over time. This
is distinct from functional correctness (handled by tests) and security
(handled by `code-quality-reviewer`). The target is the *friction* a reader
experiences when encountering unfamiliar code.

The primary output is **`COGNITIVE_DEBT.md`**, a structured report written to
the project. The conversation response is a brief digest only.

---

## Step 1 — Resolve Scope

Determine what to analyse, in order of precedence:

1. **Inline path argument** — if invoked as `/cognitive-debt <path>`, use that path.
2. **Context files** — if the user attached or mentioned specific files or
   folders, restrict analysis to those.
3. **Full project** — default when no path is specified.

Announce the resolved scope before continuing:
> "Analysing scope: `<resolved path or 'full project'>`"

---

## Step 2 — Load Reference Documents

Read both reference files and keep them in context throughout the analysis:

```
<skill_base_path>/references/debt-categories.md
<skill_base_path>/references/judgment-guidelines.md
```

`debt-categories.md` defines exactly what to look for in each of the seven
debt categories, including per-language heuristics and calibrated thresholds.

`judgment-guidelines.md` defines when NOT to flag something — intentional
design, language idioms, and legitimate trade-offs. Apply these throughout.

---

## Step 3 — Measure Codebase Size

Glob for source files (excluding `node_modules`, `.git`, `target`,
`__pycache__`, `dist`, `build`, `.next`, `vendor`, lock files, and generated
files). Count total lines of code across the matched files.

Choose analysis mode based on LOC:

| Mode | Threshold | Approach |
|------|-----------|----------|
| **Exhaustive** | < 500 LOC | Read every source file in full |
| **Structural + Sampled** | 500–5 000 LOC | Read all files structurally (names, signatures, imports); deep-read a representative 20% sample spread across layers/modules |
| **Sampled** | > 5 000 LOC | Glob tree to 3 levels; deep-read 3–5 files per top-level module or directory; prioritise files with highest churn indicators (many contributors, recently modified, longest files) |

Announce the mode chosen and the LOC count.

---

## Step 4 — Identify Languages and Load Heuristics

Infer primary language(s) from file extensions. For each detected language,
note which per-language heuristics from `debt-categories.md` apply.

If the codebase mixes languages, apply heuristics for each language to its
own files only. Do not apply Python heuristics to Go files, etc.

---

## Step 5 — Analyse Each Debt Category

Work through all seven categories defined in `debt-categories.md`:

| # | Category | Focus |
|---|----------|-------|
| D1 | **Dead Code** | Unused functions, unreachable branches, commented-out blocks, always-on/off feature flags |
| D2 | **Over-Engineering** | ABCs with one implementation, plugin registries for fixed sets, builders for trivial objects, premature generics |
| D3 | **Duplication** | Exact, structural, and semantic repetition; magic constants repeated across files |
| D4 | **Abstraction Quality** | Leaky or misnamed abstractions, god objects, shallow wrappers, anemic models |
| D5 | **Control Flow Complexity** | Deep nesting, implicit state machines, exception-driven flow |
| D6 | **Naming** | Non-predicate booleans, implementation-describing names, opaque abbreviations |
| D7 | **Test Debt** | Over-mocking, skipped tests, trivial assertions |

For every finding, capture:

- **Category tag** — `[D1]`–`[D7]`
- **Severity** — one of `🔴 HIGH`, `🟡 MEDIUM`, or `🟢 LOW` (see rules below)
- **File + line reference** — `path/to/file.py:42`
- **Evidence** — quote the specific code that demonstrates the problem
- **Why it hurts** — the concrete cognitive cost (not abstract principle)
- **Recommendation** — actionable fix, specific to this codebase
- **Confidence** — `CERTAIN`, `LIKELY`, or `UNCERTAIN` (flag uncertainty
  inline, never hide it)

### Severity Rules

| Severity | When to use |
|----------|-------------|
| 🔴 **HIGH** | Significant ongoing maintenance burden; any reader unfamiliar with this code will be meaningfully slowed or misled; the pattern is almost certainly unintentional or has clearly outlived its purpose |
| 🟡 **MEDIUM** | Measurable friction for a moderately experienced reader; trade-offs exist but the current implementation leans toward the costly side; might be intentional |
| 🟢 **LOW** | Minor friction; reasonable engineers could disagree; flagging for completeness only |

Apply `judgment-guidelines.md` rigorously before assigning any severity.
When in doubt, downgrade one level and add `[UNCERTAIN]` inline.

### What's Working Well

As you analyse, note patterns that demonstrate low cognitive load: clear naming,
well-bounded abstractions, appropriate complexity level, etc. Collect these for
the report's "What's Working Well" section.

---

## Step 6 — Load the Report Template

Read the output template from:

```
<skill_base_path>/templates/COGNITIVE_DEBT.md
```

Replace `{{ISO_DATE}}` with today's date, `{{SCOPE}}` with the scope from
Step 1, `{{LOC}}` with the line count, `{{MODE}}` with the analysis mode,
and `{{LANGUAGES}}` with the detected language(s). Then fill every section
with the findings from Step 5.

---

## Step 7 — Choose the Output Location

Pick the first location that exists or can be created, in this priority order:

| Priority | Path | Use when |
|----------|------|----------|
| 1 | `.claude/COGNITIVE_DEBT.md` | `.claude/` directory already exists |
| 2 | `docs/COGNITIVE_DEBT.md` | `docs/` directory already exists |
| 3 | `COGNITIVE_DEBT.md` | fallback — write to project root |

If a `COGNITIVE_DEBT.md` already exists at the chosen location, overwrite it
entirely — the new analysis supersedes the old one.

---

## Step 8 — Write Brief Digest to Conversation

After writing the file, output a brief digest in the conversation:

```
✓ Cognitive debt analysis complete.

Report written to : <chosen path from Step 7>
Scope             : <scope>
LOC analysed      : <N>
Analysis mode     : <exhaustive | structural + sampled | sampled>

Findings summary:
  🔴 HIGH   : N
  🟡 MEDIUM : N
  🟢 LOW    : N

Top 3 priority items:
  1. <one-line description> — <file:line>
  2. <one-line description> — <file:line>
  3. <one-line description> — <file:line>

Full evidence and recommendations are in the report file.
```

---

## Skill Rules

- **Never modify source files.** This skill is read-only. Output goes to
  `COGNITIVE_DEBT.md` only.
- **Cite real code.** Every finding must quote specific lines. Never describe
  a problem without a file:line reference.
- **Apply judgment guidelines.** Intentional design, language idioms, and
  deliberate trade-offs must not be flagged as debt. Read
  `judgment-guidelines.md` and apply it throughout.
- **Flag uncertainty.** When a pattern could be intentional or you lack full
  context, mark it `[UNCERTAIN]` and lower the severity. Never hide doubt.
- **Distinguish objective from subjective.** Only raise findings that a
  neutral, experienced engineer in the target language would agree represent
  friction. Pure stylistic preferences do not qualify.
- **Language respect.** Do not apply idioms from one language to another.
  Rust's trait objects, Python's duck typing, and Go's explicit error returns
  are features, not debt, in their respective ecosystems.
- **Scale appropriately.** In large codebases, prefer finding the most
  impactful examples of each debt category over exhaustive enumeration. Five
  HIGH findings with strong evidence are more useful than fifty LOW findings.
- **Read, don't infer.** Always open files to confirm patterns. Never assume
  a function is unused without checking call sites.

---

## Chatbot System Prompt Module

When embedding this skill as a system prompt module rather than a slash
command, prepend the following block to the system prompt:

```
You are a senior engineer specialising in code readability and maintainability.
When the user provides code or a codebase, analyse it for cognitive debt across
seven categories:

  D1 — Dead Code:             unused functions, unreachable branches, stale flags
  D2 — Over-Engineering:      unnecessary abstractions, premature generics
  D3 — Duplication:           exact, structural, and semantic repetition
  D4 — Abstraction Quality:   leaky abstractions, god objects, anemic models
  D5 — Control Flow:          deep nesting, implicit state machines
  D6 — Naming:                non-predicate booleans, opaque abbreviations
  D7 — Test Debt:             over-mocking, skipped tests, trivial assertions

Severity: 🔴 HIGH / 🟡 MEDIUM / 🟢 LOW. Flag uncertainty inline with [UNCERTAIN].
Do not pathologize intentional design or language idioms. Distinguish objective
friction from style preferences. For every finding: cite the line, quote the
code, explain the cognitive cost, and provide a concrete recommendation.
End with a "What's Working Well" section.
```
