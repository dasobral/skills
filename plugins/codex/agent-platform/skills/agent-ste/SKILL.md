---
name: agent-ste
description: 'Use when rewriting user or planner instructions before planning or execution;
  when prompts contain vague verbs (optimize, improve, better, appropriate, reasonable,
  quickly, carefully, as needed, if necessary); when multiple agents or LLMs must
  interpret the same task reproducibly; when an instruction lacks explicit actor,
  inputs, outputs, success criteria, failure conditions, ordering, or scope; or when
  preparing handoffs between orchestrators and workers.

  '
license: MIT
metadata:
  source_platform: portable
  ingested_by: skills-export
---

# Agent STE (Agent Simplified Technical English)

Rewrite instructions into a controlled natural language optimized for LLM
execution: explicit, measurable, ordered, and reproducible across models.

**Core principle:** Prefer deterministic execution over natural prose.
Explicitness beats brevity. Unambiguous wording beats elegant wording.

**Inspiration:** Principles behind ASD-STE100 (controlled language for clarity).
This skill is **not** ASD-STE100 and does not claim compliance. See
`references/principles.md`.

## When to Use

- Before planning or executing non-trivial work
- Before dispatching subagents or cross-model handoffs
- When the prompt contains forbidden vague language (see below)
- When success would be judged differently by two competent agents

**When NOT to use**

- Pure chitchat or one-line factual Q&A with no side effects
- Already-formal specs (OpenAPI, JSON Schema, RFC text) that need no rewrite
- Emergency stop / safety refusal wording that must stay short and human

## Transformation Algorithm

Execute these steps in order. Do not skip steps under time pressure.

1. **Objective** — State exactly one primary deliverable in one sentence. Do not
   join independent goals with “and” inside `OBJECTIVE`.
2. **Entities** — List every actor, system, file, service, and artifact. Assign
   a stable identifier (`SVC-API`, `FILE-auth.ts`, `AGENT-worker`).
3. **Glossary** — For each critical term, fix one meaning. Ban synonyms for
   those terms inside the instruction.
4. **Demote vagueness** — Replace every forbidden pattern with a measurable or
   observable statement (`references/rules.md`).
5. **Split actions** — One action per sentence. One objective per instruction
   block. Use a numbered list for ordering.
6. **Fill slots** — Complete the template in `templates/instruction-block.md`
   (actor, object, inputs, outputs, assumptions, constraints, preconditions,
   postconditions, invariants, success, failure, rollback, idempotency,
   side effects, permissions, dependencies, artifacts, validation, checklist).
7. **Scope fence** — State what is in scope and what is out of scope.
8. **Self-check** — Answer every item in `references/checklist.md` with YES/NO.
   If any required item is NO, revise before planning or execution.

## Mandatory Rules (summary)

Full normative list: `references/rules.md`.

| Rule | Why |
|------|-----|
| One action per sentence | Prevents partial execution and skipped conjuncts |
| One objective per instruction block | Stops silent scope expansion |
| One meaning per critical word | Removes synonym drift across LLMs |
| Explicit actor + object | No orphan imperatives |
| Explicit inputs + outputs | Makes dataflow checkable |
| Explicit success + failure | Defines done vs retry vs abort |
| Explicit ordering | `1 → 2 → 3` or mark `PARALLEL` |
| Explicit units + identifiers | No “soon”, “large”, “the file” |
| No pronouns when ≥2 entities | “It/they/this” is an entity bug |
| No forbidden vague lexicon | Forces observables |

## Forbidden Patterns (detect and rewrite)

`optimize` · `improve` · `better` · `appropriate` · `reasonable` · `quickly` ·
`carefully` · `if necessary` · `as needed` · `etc.` · `and so on` · `normally` ·
`probably` · `maybe` · `somehow` · `tidy` · `harden` · `fix up` ·
`make sure` (without a checkable predicate) · `satisfied` · `obvious`

Rewrite table and agent-oriented slots: `references/rules.md`.

## Output Contract

Emit an Agent STE block using `templates/instruction-block.md`. Then either:

- execute that block, or
- hand it to the next agent unchanged

Do not plan from the original vague prompt once an Agent STE rewrite exists.

## Examples and Spec

- Worked rewrites (coding, DevOps, docs, Git, research, debug, infra, security):
  `references/examples.md`
- Objective compliance checklist: `references/checklist.md`
- Future machine-checkable spec (MUST/SHOULD/MAY, JSON/YAML, linting, MCP):
  `references/spec-v1.md`

## Limitations

- Does not replace domain expertise or formal verification
- Cannot invent missing requirements; mark `UNKNOWN` and halt or ask
- Numeric targets require a source (user, SLO, benchmark); else state
  `METRIC-SOURCE: UNKNOWN` and do not fabricate thresholds
- Over-application to trivial chat wastes tokens — respect When NOT to use
- Not a license to ignore higher-priority safety or repository rules

## Rationalizations — Do Not Skip

| Excuse | Reality |
|--------|---------|
| "Too simple to rewrite" | Simple vague prompts still fork across models |
| "No time for slots" | Missing success criteria causes expensive rework |
| "Context implies the metric" | Another LLM does not share your implied context |
| "I'll keep optimize but add detail" | Forbidden lexicon remains non-deterministic |
| "Pronouns are fine; there are only two things" | Two things is exactly when pronouns collide |
| "Rollback is overkill for a docs tweak" | State `ROLLBACK: none — read-only` explicitly |
| "One OBJECTIVE can list three goals with and" | That is three blocks or gated phases — split them |

**Red flags — STOP and rewrite:** residual `etc.`; success = “looks good”;
actor missing; two actions joined by “and”; synonym pairs for the same concept;
`if necessary` without a boolean predicate.
