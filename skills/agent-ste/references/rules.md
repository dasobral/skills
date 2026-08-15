# Agent STE — Mandatory Rules and Forbidden Patterns

## Mandatory Rules

Each rule includes the failure it prevents.

### R1 — One action per sentence

**Rule:** Write exactly one imperative action per sentence.  
**Why:** Models under pressure execute the first conjunct and skip the rest.  
**Bad:** `Update the client and redeploy the service.`  
**Good:**  
1. `AGENT-worker update FILE-client-sdk to match SCHEMA-api@2.1.0.`  
2. `AGENT-worker redeploy SVC-api to ENV-staging using PIPELINE-deploy.`

### R2 — One objective per instruction block

**Rule:** One `OBJECTIVE` field with one primary deliverable. Do not join independent
deliverables with “and” inside `OBJECTIVE` (e.g. latency + error format + production
deploy). Put follow-on deliverables in a second Instruction Block, or move them to
`SCOPE.OUT` / a gated later phase named in FAILURE/SUCCESS only as a dependency.  
**Why:** Multi-objective prompts invite silent prioritization differences across LLMs.  
**Bad:** `Reduce latency and improve errors and deploy to prod.`  
**Good:** `Reduce P95 latency of EP-GET-/v1/orders from 800ms to ≤400ms on ENV-staging.`  
(Error-format work and prod deploy are separate blocks, or explicit later phases with their own success gates.)

### R3 — One meaning per critical word

**Rule:** Declare a glossary for every term that affects behavior. Ban synonyms for those terms inside the block.  
**Why:** “Fix”, “repair”, and “resolve” trigger different tool policies in different models.

### R4 — Explicit actor

**Rule:** Every action names who performs it (`AGENT-*`, `HUMAN-*`, `TOOL-*`, `CI-*`).  
**Why:** Orphan imperatives leave authority unclear (agent vs human vs automation).

### R5 — Explicit object

**Rule:** Every action names the object by stable ID (file path, service name, PR number).  
**Why:** “Update the service” is not addressable.

### R6 — Explicit inputs and outputs

**Rule:** List inputs with source/format; list outputs with destination/format.  
**Why:** Makes dataflow and caching/idempotency checkable.

### R7 — Explicit success criteria

**Rule:** Success is a checkable predicate (command + expected result, metric + threshold, diff property).  
**Why:** “Looks good” / “satisfied” is not reproducible.

### R8 — Explicit failure conditions

**Rule:** For each likely failure, state the predicate and the action (`retry n`, `abort`, `rollback`, `escalate`).  
**Why:** Without this, agents improvise incompatible recovery strategies.

### R9 — Explicit assumptions and constraints

**Rule:** Write assumptions with an IF FALSE branch. Write constraints with units/limits.  
**Why:** Hidden assumptions are the main cross-model divergence source.

### R10 — Explicit ordering

**Rule:** Number steps. If two steps may run concurrently, mark `PARALLEL: A || B`. Otherwise sequential order is mandatory.  
**Why:** Unordered bullets are not a schedule.

### R11 — Explicit units

**Rule:** Quantities include units (`ms`, `MB`, `%`, `count`, `exit code`).  
**Why:** “Faster” and “small” are not observables.

### R12 — Explicit identifiers and references

**Rule:** Use stable IDs; reference commits, PRs, ticket IDs, API versions, and absolute or repo-root paths.  
**Why:** “The recent change” is not a pointer.

### R13 — Explicit scope

**Rule:** State `SCOPE.IN` and `SCOPE.OUT`.  
**Why:** Prevents drive-by refactors and surprise dependency upgrades.

### R14 — No ambiguous pronouns for multiple entities

**Rule:** If two or more entities are in play, repeat the ID; do not use `it`, `they`, `this`, `that`.  
**Why:** Pronoun resolution differs across models.

### R15 — Agent slots are mandatory for mutating work

**Rule:** For any instruction that may mutate state, fill: preconditions, postconditions, invariants, rollback, idempotency, side effects, permissions, external dependencies, expected artifacts, validation procedure, completion checklist.  
**Why:** These are the agent hazards ASD-STE100 never covered.  
**Read-only exception:** Set `ROLLBACK: NONE — read-only`, `SIDE EFFECTS: NONE`, and still fill validation.

## Forbidden Patterns → Required Rewrites

| Forbidden | Problem | Rewrite pattern |
|-----------|---------|-----------------|
| optimize | No dimension/target | `Reduce P95 latency of EP-GET-/v1/orders from 800ms to ≤400ms` |
| improve / better | Relative with no baseline | `Increase unit-test pass rate on BRANCH-main from 97% to 100%` |
| appropriate / reasonable | Hidden judgment | Name the policy, RFC, or checklist item |
| quickly / carefully | Non-operational adverbs | Replace with timebox (`≤15 min`) or validation steps |
| if necessary / as needed | Missing predicate | `IF <boolean check> THEN <action> ELSE <action>` |
| etc. / and so on | Open set | Enumerate the closed set or write `ONLY: {a,b,c}` |
| normally / usually | Unstated exception path | State the default and the exception predicate |
| probably / maybe / somehow | Non-deterministic hedge | State fact, or `UNKNOWN` + halt/ask |
| tidy / clean up | Unscoped edits | Name files and allowed edit types |
| harden | Security theater verb | Name CWE/control and verification |
| fix up / sort out | Undefined end state | Define postcondition + validation |
| make sure | Often uncheckable | `VERIFY: <command> → <result>` |
| satisfied / looks good / obvious | Subjective gate | Replace with checklist predicates |

## Baseline Failures This Skill Targets

Observed without Agent STE (pressure tests):

- Kept “tighten”, “tidy”, “reasonable hardening”, “sanity-check”, “when satisfied”
- Omitted measurable success criteria and rollback
- Left entity identity unresolved (“find the service and client”)
- Used open-ended “whatever the project uses” instead of named inputs
- Treated deploy as optional judgment without a boolean predicate

**Counter-rule:** Under time pressure, still complete the template. Shorter vague prose is not faster end-to-end.

## Allowed Flexibility

- Sentence length may exceed 25 words when a single path, command, or URL forces it.
- Domain jargon is allowed if defined in the glossary.
- Formal artifacts (schemas, OpenAPI) may be referenced by ID instead of restated.
- `UNKNOWN` is allowed; fabrication is not.
