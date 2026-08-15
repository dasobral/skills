# Agent STE — Purpose, Philosophy, and ASD-STE100 Adaptation

## Purpose

Agent STE is a controlled natural language for AI agent instructions. It sits
between ordinary English and formal specification languages. Humans can still
read it; machines can interpret it with less ambiguity.

Use Agent STE to maximize:

1. Instruction clarity
2. Deterministic interpretation
3. Reproducibility across runs
4. Machine readability
5. Interoperability between different LLMs and agent runtimes
6. Reduction of ambiguity

## Philosophy

1. **Execution over eloquence** — The instruction is a contract for action, not
   a narrative.
2. **Explicit over implicit** — If two agents could disagree, write the
   deciding fact down.
3. **Local control, not global vocabulary tyranny** — Fix meanings for terms
   that matter in *this* instruction; do not force an aerospace dictionary.
4. **Observables over intentions** — Prefer commands, exit codes, paths,
   metrics, and diffs over “quality” adjectives.
5. **Fail closed on UNKNOWN** — Missing requirements become `UNKNOWN` with a
   halt/ask branch, not creative fill-in.
6. **Inspiration, not compliance** — Agent STE derives principles from
   ASD-STE100. It is not ASD-STE100 and must not be labeled as such.

## Why ASD-STE100 Exists (relevant mechanics)

ASD-STE100 reduces misunderstanding in high-stakes technical procedures by:

- Restricting vocabulary and allowing **one approved meaning** per word
- Preferring **short, active, imperative** sentences
- Requiring **one instruction per sentence**
- Separating procedures from descriptions
- Making documentation easier to translate and follow consistently

Those mechanics exist because ambiguity causes incorrect action. For AI agents,
incorrect action is the default failure mode of vague prompts.

## What Transfers to Agents

| ASD-STE100 idea | Agent STE adaptation | Why it remains useful |
|-----------------|----------------------|------------------------|
| One instruction per sentence | Same | Models drop conjuncts under load |
| One topic / clear structure | One objective per block + slotted sections | Prevents scope creep |
| One meaning per word | Local glossary for critical terms | Stops synonym drift across LLMs |
| Active voice | Explicit `ACTOR` + imperative verb | Names who acts (agent, tool, human) |
| Avoid complex verb forms | Simple tense; no “should maybe try” | Modal hedges are non-executable |
| Vertical lists | Numbered ordered actions | Deterministic ordering |
| Be specific | Units, IDs, paths, exit codes | Machine-checkable predicates |

## What to Modify or Discard

| ASD-STE100 idea | Agent STE decision | Why |
|-----------------|--------------------|-----|
| ~900-word approved dictionary | Discard as hard constraint | Agent tasks need domain jargon; use local glossary instead |
| Strict 20/25 word sentence caps | Soft target ≤25 words; allow longer for identifiers | Paths and command lines exceed caps legitimately |
| Ban many ordinary English words | Discard | Over-restriction harms coding/DevOps prompts |
| Human maintenance/safety warning formats | Replace with agent slots (rollback, permissions, side effects) | Different hazard model |
| Optimize for non-native human readers | Optimize for multi-model execution | Primary reader is an LLM runtime |
| Translation cost reduction | Keep as secondary benefit | Still helps human review of agent plans |

## Agent-Oriented Extensions (not in ASD-STE100)

Agents mutate repositories, cloud accounts, and production systems. Agent STE
therefore requires slots that maintenance English never needed:

| Slot | Role |
|------|------|
| Preconditions | Gate start |
| Postconditions | Define world-after-success |
| Invariants | Protect properties during work |
| Success / failure criteria | Branch retry vs abort |
| Rollback | Reverse partial mutation |
| Idempotency | Safe re-run semantics |
| Deterministic ordering | Sequence or explicit PARALLEL |
| Side effects | Name external mutations |
| Permissions required | Authz before attempt |
| External dependencies | Tools, APIs, MCP servers |
| Expected artifacts | Concrete deliverables |
| Validation procedure | How to prove success |
| Completion checklist | Final gate |

## Design Position

```text
Ordinary English  →  Agent STE  →  Formal specs (JSON Schema, RFC, TLA+)
     ↑ readable           ↑ controlled CNL        ↑ fully formal
     ↓ ambiguous          ↓ explicit slots        ↓ heavy to author
```

Agent STE is the practical middle: fast to write, strict enough for handoffs.
