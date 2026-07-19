# Agent STE (Agent Simplified Technical English) — Design

Date: 2026-07-19  
Status: Approved for autonomous implementation (cloud agent; full user spec provided)

## Problem

Ordinary English instructions for AI agents are ambiguous. Different LLMs interpret the same prompt differently. Vague verbs (`optimize`, `improve`, `harden`), implicit actors, missing success/failure conditions, and synonym drift reduce reproducibility and interoperability.

ASD-STE100 solves a related problem for human aerospace maintainers: controlled vocabulary, one meaning per word, one instruction per sentence, short active sentences. Agent STE adapts those *principles* for LLM execution rather than human maintenance manuals.

## Goals

Maximize:

1. Instruction clarity
2. Deterministic interpretation
3. Reproducibility across runs
4. Machine readability
5. Interoperability across LLMs / agent runtimes
6. Ambiguity reduction

Prefer: deterministic execution over natural prose; explicitness over brevity; unambiguous wording over elegant wording.

## Non-goals

- Teach ASD-STE100 verbatim or claim ASD compliance
- Restrict vocabulary to ~900 aerospace words
- Optimize for human literary style
- Replace formal specs (OpenAPI, JSON Schema, RFC) — Agent STE sits between ordinary English and formal specs

## Placement in this repository

| Item | Location |
|------|----------|
| Authoring drop | `landing/skills/agent-ste/` |
| Plugin assignment | `agent-platform` (instruction contracts before create-agent / orchestrate) |
| Source of truth after ingest | `core/skills/agent-ste/` |
| Generated outputs | `plugins/cursor/agent-platform/`, `plugins/codex/agent-platform/`, flat `dist/` |

## Skill shape

```
agent-ste/
  SKILL.md                      # invocation, algorithm, quick rules, checklist pointer
  references/
    principles.md               # philosophy + ASD-STE100 adaptation rationale
    rules.md                    # mandatory rules + forbidden patterns + rewrites
    examples.md                 # 8 domain transformations with superiority notes
    checklist.md                # objective yes/no compliance checklist
    spec-v1.md                  # stretch: Agent STE Specification v1.0 (RFC-style)
  templates/
    instruction-block.md        # reusable instruction skeleton
```

`SKILL.md` stays procedural and relatively short. Heavy reference lives in `references/` so agents load detail only when rewriting.

## Core design decisions

### 1. Controlled natural language, not a formal DSL

Agent STE remains readable English with required slots (actor, object, inputs, outputs, success/failure, ordering). It is not YAML-only; YAML/JSON serialization is a stretch-goal lint target.

### 2. Keep useful ASD-STE100 principles; discard human-aerospace specifics

| Keep / adapt | Discard or relax |
|--------------|------------------|
| One instruction per sentence | Strict ~900-word dictionary |
| One meaning per approved term (local glossary) | 20/25 word hard caps (prefer ≤25; allow longer when identifiers force it) |
| Active voice + explicit actor | Ban on technical verbs outside dictionary |
| Avoid pronouns when multiple entities | Maintenance/safety warning formats |
| Vertical lists for complex steps | Aerospace technical-name taxonomy |

### 3. Agent-oriented extensions (beyond ASD-STE100)

Required instruction blocks when rewriting for execution:

- Preconditions / postconditions / invariants
- Success criteria / failure conditions
- Rollback / idempotency
- Side effects / permissions / external dependencies
- Expected artifacts / validation procedure / completion checklist
- Deterministic ordering

### 4. Transformation algorithm (normative for the skill)

1. Identify objective (one primary objective)
2. Extract entities; assign stable identifiers
3. Replace vague language with measurable statements
4. Split into one-action sentences
5. Fill mandatory slots (template)
6. State ordering, assumptions, constraints
7. Run compliance checklist
8. Emit Agent STE instruction block

### 5. Testing approach (skill TDD)

- RED: baseline rewrites of vague prompts without the skill (expect residual vagueness, missing criteria)
- GREEN: same scenarios with skill loaded (expect slot-complete, measurable rewrites)
- REFACTOR: close loopholes (e.g. “optimize latency” without a numeric target)

## Success criteria for this deliverable

- [ ] Portable skill with purpose, philosophy, invocation, algorithm, rules, forbidden patterns, examples, checklist, limitations
- [ ] Eight example domains covered
- [ ] Spec v1.0 stretch doc with MUST/SHOULD/MAY and lint/serialization notes
- [ ] Ingested into core and exported via `skills-maintain`
- [ ] Validation checklist items are objectively answerable yes/no

## Risks

- Over-verbosity may slow casual chats — mitigated by clear “when NOT to use”
- Agents may treat checklist as optional under time pressure — mitigated by mandatory gate before planning/execution
- Not claiming trademark/compliance with ASD-STE100 — disclaim inspiration-only in principles
