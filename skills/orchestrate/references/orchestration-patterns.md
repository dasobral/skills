# Orchestration Patterns Reference

This reference describes common multi-agent pipeline topologies, their
sequencing rules, data routing strategies, and when to use each pattern.
The orchestrator consults this guide during Step 5 (Build the Execution Plan)
to select the appropriate execution strategy.

---

## Pipeline Topologies

### 1. Linear Pipeline (Chain)

**Shape**: A → B → C → … → Z

**When to use**:
- Each step transforms the output of the prior step.
- There is a single stream of data with no branching.
- Classic ETL-style workflows (extract → transform → load).

**Sequencing**: Fully sequential. Each agent waits for its predecessor.

**ASCII DAG**:
```
[T1: agent-a] ──→ [T2: agent-b] ──→ [T3: agent-c]
```

**Data routing**: Pass the full output artifact of Tn as the sole input to T(n+1).

**Failure impact**: High — a failure at any node blocks all downstream nodes.
Apply strict failure policy at early stages.

---

### 2. Fan-Out (Parallel Branches)

**Shape**: A → (B ∥ C ∥ D)

**When to use**:
- One agent produces output that can be independently processed by multiple
  specialised agents simultaneously.
- Reduces total wall-clock time when branch agents are slow.
- Example: a splitter agent creates independent work items for parallel workers.

**Sequencing**: T1 sequential; T2, T3, T4 in parallel (single `Agent` tool
call block with multiple invocations).

**ASCII DAG**:
```
                 ╔══→ [T2: agent-b]
[T1: agent-a] ══╠══→ [T3: agent-c]
                 ╚══→ [T4: agent-d]
```

**Data routing**: Slice T1's output into independent sub-artifacts. Each branch
agent receives only its slice, not the full output.

**Failure impact**: Medium — branch failures are independent. A failed branch
does not necessarily block other branches (depends on merger policy).

---

### 3. Fan-In (Merge / Aggregator)

**Shape**: (A ∥ B ∥ C) → D

**When to use**:
- Multiple independent agents produce partial results that must be combined.
- All branch outputs are available before the merger agent runs.

**Sequencing**: T1, T2, T3 in parallel; T4 sequential after all three complete.

**ASCII DAG**:
```
[T1: agent-a] ══╗
[T2: agent-b] ══╬══→ [T4: merger]
[T3: agent-c] ══╝
```

**Data routing**: Pass all branch output artifacts as a combined input to T4.
Define the merger's input contract as a list/map of partial results.

**Failure impact**: If any branch fails, the merger cannot run — escalate
immediately. Consider whether partial results are acceptable (define this in
the failure policy).

---

### 4. Diamond (Fan-Out then Fan-In)

**Shape**: A → (B ∥ C) → D

**When to use**:
- A root agent provides context; two specialised agents work in parallel on
  different aspects; a final agent synthesises both.
- Example: reader → (domain-analyzer ∥ security-analyzer) → report-writer.

**Sequencing**: T1 sequential; T2 and T3 in parallel; T4 sequential after
both T2 and T3 complete.

**ASCII DAG**:
```
[T1: root] ══╗
             ╠══→ [T2: agent-b] ══╗
             ╚══→ [T3: agent-c] ══╩══→ [T4: synthesizer]
```

**Data routing**:
- T1 → T2 and T1 → T3: pass the same artifact (or different slices).
- T2 + T3 → T4: merge both outputs; define separate named slots
  (`T2_output`, `T3_output`) in T4's input.

**Failure impact**: Any failure in T2 or T3 blocks T4. Apply independent retry
policies to each branch.

---

### 5. Map-Reduce

**Shape**: A → [B × N items] → C

**When to use**:
- A splitter produces N independent work items.
- The same agent type is applied to each item independently (map phase).
- A reducer agent aggregates all N results.
- Useful for large documents (chunk → analyse each chunk → summarise).

**Sequencing**: T1 sequential; T2[1..N] all in parallel; T3 sequential after
all map agents complete.

**ASCII DAG**:
```
                  ╔══→ [T2a: worker] ══╗
[T1: splitter] ══╠══→ [T2b: worker] ══╬══→ [T3: reducer]
                  ╚══→ [T2c: worker] ══╝
```

**Data routing**: T1 produces a list of items. Instantiate one agent call per
item. Each worker receives a single item. Reducer receives the list of all
worker outputs.

**Implementation note**: Use a single `Agent` tool message with N parallel
invocations for the map phase.

---

### 6. Conditional Branch (Router)

**Shape**: A → (B if condition-x, C if condition-y)

**When to use**:
- The output of one agent determines which agent runs next.
- Example: a classifier agent routes to either a "simple-handler" or a
  "complex-handler" based on document type.

**Sequencing**: T1 sequential; the orchestrator reads T1's output and
conditionally invokes T2 **or** T3 (never both).

**ASCII DAG**:
```
[T1: router] ──→ [T2: handler-a]  (if condition X)
             └──→ [T3: handler-b] (if condition Y)
```

**Data routing**: T1 must include a routing signal in its output contract
(e.g. a `route` field in a JSON envelope). The orchestrator reads this field
to select the next agent.

**Implementation note**: Define the routing conditions in the task graph. Do
not embed routing logic inside an agent — the orchestrator owns routing.

---

## Sequencing Decision Rules

Apply these rules in order when building the execution plan:

| Rule | Condition | Decision |
|------|-----------|----------|
| **R1** | Subtask has no dependencies listed | Run in Phase 1 (or earliest available phase) |
| **R2** | All of a subtask's dependencies are in Phase N | Place subtask in Phase N+1 |
| **R3** | Two subtasks are in the same phase with no dependency between them | Run them in **parallel** |
| **R4** | Subtask produces a routing signal that determines which subtask runs next | Run the router first; select the branch after inspecting its output |
| **R5** | Subtask is a merger/reducer that requires all branch outputs | Do not start until **all** branches in the prior phase have completed |

---

## Data Routing Best Practices

### Always use named artifact slots

Name every artifact that flows between agents:
```
T1_output: doc_sections   (JSON array)
T2_output: analysis       (Markdown)
T3_output: final_report   (Markdown)
```

Never refer to "the previous agent's output" — always use the slot name.

### Define schema at every edge

For each handoff edge, specify at minimum:
- **Format**: JSON / Markdown / plain text / CSV / binary
- **Required structure**: schema or required section headers
- **Size constraints** if relevant (e.g. "≤ 500 words", "array of ≤ 200 items")

### Validate before routing

Before passing an artifact to the next agent, verify:
1. The artifact is non-empty.
2. Required top-level fields/sections are present.
3. The format is as expected.

If validation fails, apply the failure policy rather than passing invalid data
downstream (garbage-in-garbage-out amplification is a major pipeline risk).

### Extract, don't relay

Never pass raw agent conversation transcripts as input to the next agent.
Always extract only the declared artifact from the agent's response. This
prevents context bleed and keeps handoff contracts clean.

---

## Failure Handling Cheatsheet

| Scenario | Recommended action |
|----------|--------------------|
| Agent returns empty output | Retry once with explicit output format reminder |
| Agent returns wrong format | Retry once with schema/example in the prompt |
| Agent raises an error | Log full error + inputs; retry up to 2× with backoff |
| Agent cannot complete task (missing capability) | Do not retry; escalate immediately with agent name and capability gap |
| Upstream agent failed; dependent agent cannot run | Mark dependent as BLOCKED; include in escalation report |
| All retries exhausted | Emit escalation report; surface best partial result if available |

**Retry backoff**: wait 2 s before first retry, 4 s before second. Do not
retry more than twice per subtask.

**Partial results policy**: Define explicitly in the task graph whether partial
pipeline execution (some subtasks completed, some failed) constitutes a
usable deliverable. Default: partial results are surfaced with clear labelling
but not presented as a final deliverable.

---

## Agent Definition Conventions (Recommended)

Agent `.md` files work best with the orchestrator when they include:

```yaml
---
name: <kebab-case-name>
role: <one-line role description>
input: <what the agent expects — format and content>
output: <what the agent produces — format and content>
capabilities:
  - <capability 1>
  - <capability 2>
---
```

The orchestrator extracts these fields in Step 2 to build the registry. Without
frontmatter, the orchestrator infers from headings and prose — which is less
reliable. Agents without explicit `input:` and `output:` fields increase the
risk of handoff contract mismatches.

Minimum viable agent definition (no frontmatter):

```markdown
# Agent Name

<One paragraph role description>

## Input
<What the agent needs>

## Output
<What the agent produces and in what format>
```
