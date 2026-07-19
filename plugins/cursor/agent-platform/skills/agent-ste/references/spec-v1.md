# Agent STE Specification v1.0 (Draft Proposal)

Status: Draft  
Schema ID: `agent-ste/1.0`  
Language: English (controlled)  
Relation to ASD-STE100: Inspired by principles only; **not** an ASD standard

This document proposes a future normative specification. The skill in
`SKILL.md` implements Agent STE **0.1** practice. v1.0 is the machine-checkable
target.

## 1. Normative terminology

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
are to be interpreted as described in RFC 2119 / RFC 8174.

| Term | Definition |
|------|------------|
| Instruction Block | A single Agent STE document with one OBJECTIVE |
| Entity | A named actor, system, file, service, artifact, or secret with a stable ID |
| Stable ID | `[A-Z][A-Z0-9-]{1,63}` identifier unique within the block |
| Checkable predicate | A statement verifiable by command output, metric query, file inspection, or exit code |
| Mutating instruction | Any block that may create/update/delete state outside the agent's scratch memory |
| Lint | Automated static check of an Instruction Block |

## 2. Conformance levels

| Level | Name | Meaning |
|-------|------|---------|
| L0 | Lexical | Forbidden lexicon absent; one action per sentence |
| L1 | Structural | L0 + required sections present |
| L2 | Executable | L1 + checkable success/failure/validation |
| L3 | Operable | L2 + hazard slots for mutating work (rollback, permissions, etc.) |

A block conforming to this spec **MUST** declare `conformance: L0|L1|L2|L3`.

## 3. Normative rules

### 3.1 Core

1. An Instruction Block **MUST** contain exactly one `objective` string.
2. An Instruction Block **MUST** declare `entities` with ≥1 actor.
3. Every action **MUST** reference an `actor_id` that exists in `entities`.
4. Every action **MUST** reference an `object_id` OR an explicit `object_ref` path/URI.
5. Actions **MUST** be an ordered list. Concurrent actions **MUST** set `parallel_group`.
6. A block **MUST** include `scope.in` and `scope.out` arrays (arrays **MAY** be empty only if justified by `scope.note`).
7. Critical terms **MUST** appear in `glossary` with exactly one `meaning`.
8. Success criteria **MUST** be an array of checkable predicates with length ≥1.
9. Failure conditions **MUST** be an array of `{predicate, action}` with length ≥1.
10. Validation **MUST** be an ordered list of `{step, expected}` with length ≥1.

### 3.2 Lexicon

11. The following tokens **MUST NOT** appear in normative fields (case-insensitive, whole word):  
    `optimize`, `improve`, `better`, `appropriate`, `reasonable`, `quickly`, `carefully`, `if necessary`, `as needed`, `etc.`, `and so on`, `normally`, `probably`, `maybe`, `somehow`.
12. Subjective gates **MUST NOT** appear: `looks good`, `satisfied`, `obvious`, unqualified `harden`, `tidy`.
13. When `entities.length >= 2`, action text **MUST NOT** use pronouns `it`, `they`, `this`, `that` to refer to those entities.

### 3.3 Mutating work

14. If `mutating: true`, the block **MUST** include: `preconditions`, `postconditions`, `invariants`, `rollback`, `idempotency`, `side_effects`, `permissions`, `external_dependencies`, `artifacts`, `completion_checklist`.
15. If `mutating: false`, the block **MUST** set `side_effects: []` and `rollback.kind: none`.
16. Unknown required values **MUST** use `unknown: true` and `on_unknown: halt|ask`. Fabricated thresholds **MUST NOT** be used.

### 3.4 Recommendations

17. Action sentences **SHOULD** be ≤25 words unless a single identifier forces overflow.
18. Blocks **SHOULD** include `assumptions` with `if_false` branches.
19. Orchestrators **SHOULD** refuse to dispatch workers on FAIL checklist results.
20. Implementations **MAY** extend the schema with `x-` extension fields.

## 4. Machine-checkable rules (lint)

| Rule ID | Check | Severity |
|---------|-------|----------|
| ASTE-001 | Exactly one `objective` | error |
| ASTE-002 | Forbidden lexicon regex hit | error |
| ASTE-003 | Action missing `actor_id` | error |
| ASTE-004 | Dangling entity reference | error |
| ASTE-005 | Pronoun heuristic when entities≥2 | warning→error at L2 |
| ASTE-006 | `success` empty | error |
| ASTE-007 | `failure` empty | error |
| ASTE-008 | Mutating without `rollback` | error |
| ASTE-009 | Conjunction ` and ` joining two verbs in one action | warning |
| ASTE-010 | Quantity without unit token | warning |
| ASTE-011 | `etc.` or ellipsis in scope lists | error |
| ASTE-012 | `unknown` without `on_unknown` | error |

### Example lint CLI (proposed)

```bash
agent-ste lint instruction.yaml --level L3
agent-ste lint instruction.json --format sarif -o ste.sarif
```

## 5. Serialization

### 5.1 YAML

```yaml
schema: agent-ste/1.0
conformance: L3
mutating: true
objective: Deploy IMAGE-api:2.4.1 to ENV-prod using canary rollout.
entities:
  - id: AGENT-sre
    type: actor
  - id: SVC-api
    type: service
  - id: IMAGE-api:2.4.1
    type: artifact
glossary:
  - term: canary
    meaning: Weighted traffic shift to a new image with metric gates
    banned_synonyms: [careful deploy, soft launch]
scope:
  in: [SVC-api, ENV-prod traffic weights]
  out: [database migrations, DNS]
assumptions:
  - text: Change window is open
    if_false: halt
constraints:
  - error_rate_percent_max: 1
  - p95_latency_ms_max: 300
preconditions:
  - predicate: JOB-ci-e2e == green on TAG-v2.4.1
inputs: []
actions:
  - id: A1
    actor_id: AGENT-sre
    object_id: SVC-api
    text: Set canary weight to 10 percent for IMAGE-api:2.4.1.
  - id: A2
    actor_id: AGENT-sre
    object_id: SVC-api
    text: Observe METRIC-error-rate and METRIC-p95 for 20 minutes.
artifacts:
  - id: ART-deploy-log
    path: ./artifacts/deploy-prod-2.4.1.json
    format: json
outputs: []
postconditions:
  - predicate: SVC-api runs IMAGE-api:2.4.1 at 100 percent weight
invariants:
  - predicate: No production secrets written to the repository
success:
  - predicate: error_rate_percent <= 1 for 20 minutes after full rollout
  - predicate: p95_latency_ms <= 300 for 20 minutes after full rollout
failure:
  - predicate: error_rate_percent > 1 during canary
    action: rollback
validation:
  - step: Query METRIC-error-rate
    expected: <= 1 percent
rollback:
  kind: steps
  steps:
    - Set traffic to IMAGE-api:2.4.0 at 100 percent
idempotency:
  safe_to_rerun: false
  if_rerun: Read current weight before changing traffic
side_effects:
  - traffic_shift
permissions:
  - deploy-prod
external_dependencies:
  - metrics-api
completion_checklist:
  - Canary gate passed
  - Full rollout gate passed
  - Deploy log artifact written
```

### 5.2 JSON Schema (sketch)

```json
{
  "$id": "https://example.local/schemas/agent-ste-1.0.json",
  "type": "object",
  "required": [
    "schema", "conformance", "mutating", "objective",
    "entities", "scope", "actions", "success", "failure", "validation"
  ],
  "properties": {
    "schema": { "const": "agent-ste/1.0" },
    "conformance": { "enum": ["L0", "L1", "L2", "L3"] },
    "mutating": { "type": "boolean" },
    "objective": { "type": "string", "minLength": 1, "maxLength": 500 },
    "entities": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "type"],
        "properties": {
          "id": { "type": "string", "pattern": "^[A-Z][A-Z0-9:._-]{1,63}$" },
          "type": {
            "enum": ["actor", "system", "file", "service", "artifact", "secret"]
          }
        }
      }
    },
    "actions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "actor_id", "text"],
        "properties": {
          "id": { "type": "string" },
          "actor_id": { "type": "string" },
          "object_id": { "type": "string" },
          "object_ref": { "type": "string" },
          "parallel_group": { "type": "string" },
          "text": { "type": "string" }
        }
      }
    }
  }
}
```

## 6. Integration opportunities

### 6.1 MCP tools

Proposed tools:

| Tool | Purpose |
|------|---------|
| `agent_ste.lint` | Lint markdown/YAML/JSON blocks; return rule IDs |
| `agent_ste.rewrite` | Transform ordinary English → draft block (model-assisted) |
| `agent_ste.validate_checklist` | Answer checklist YES/NO programmatically |
| `agent_ste.to_plan` | Compile L3 block into planner tasks |

### 6.2 Planners and orchestrators

- Orchestrators **SHOULD** accept only L2+ blocks as worker prompts.
- Multi-model routing **SHOULD** attach the same serialized block to every worker.
- Retries **MUST** reuse the same block bytes (byte-identical) for reproducibility experiments.

### 6.3 CI

```yaml
# proposed
- name: Agent STE lint
  run: agent-ste lint prompts/**/*.yaml --level L2 --fail-on warning
```

## 7. Out of scope for v1.0

- Full natural-language understanding guarantees
- Claiming ASD-STE100 compliance
- Mandating a global 900-word dictionary
- Replacing typed API contracts

## 8. Versioning

- `agent-ste/0.1` — skill practice (markdown template)
- `agent-ste/1.0` — this draft once lint CLI + JSON Schema ship
- Breaking schema changes require major version bump
