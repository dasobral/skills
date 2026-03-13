# agent-orchestrator

A Claude Code skill that turns Claude into a **top-level orchestrator** capable
of dynamically deploying specialized agents to complete complex, multi-step
tasks. Drop any set of agent definitions (`.md` files) into an `agents/`
directory and `/orchestrate` will discover them, build an execution plan, run
the agents in the right order, route data between them, and synthesize a final
deliverable.

**Slash command**: `/orchestrate "<task>" [agents-dir]`

---

## What it does

| Capability | Description |
|-----------|-------------|
| Task decomposition | Breaks a high-level goal into subtasks with clear inputs, outputs, and dependencies |
| Agent selection | Matches subtasks to agent definitions based on role, input, and output contracts |
| Execution sequencing | Determines which agents run sequentially and which can run in parallel |
| Data routing | Passes named output artifacts from one agent as inputs to the next — no raw transcript relay |
| Failure handling | Retries transient errors (up to 2×), reformulates on contract violations, and escalates clearly on persistent failure |
| Result synthesis | Aggregates terminal agent outputs into a coherent final deliverable |

---

## Usage

### As a slash command (Claude Code)

```bash
# Basic: task description + default agents/ directory
/orchestrate "Analyse architecture.md and produce an executive summary"

# With explicit agents directory
/orchestrate "Review the API spec for security issues" path/to/my-agents/

# Fully qualified path to document
/orchestrate "Summarise the Q4 report" --agents agents/ docs/q4-report.md
```

Claude will:
1. Discover and print an **Agent Registry** from the agents directory.
2. Decompose the task into subtasks.
3. Assign agents and build a **Task Graph** with sequencing and handoff contracts.
4. Print the **Orchestration Plan** and (in interactive mode) ask for confirmation.
5. Execute the plan, printing a status line after each completed subtask.
6. Present the **final deliverable** and an orchestration summary.

### As a chatbot system prompt module

Copy the system prompt block from the bottom of `SKILL.md` into your system
prompt. Then provide the user with a task and agent definitions in the
conversation.

---

## File structure

```
agent-orchestrator/
├── SKILL.md                              # Skill definition — step-by-step orchestrator instructions
├── README.md                             # This file
├── templates/
│   └── orchestration-plan.md             # Reusable task-graph plan template
├── references/
│   └── orchestration-patterns.md         # Pipeline topologies, sequencing rules, routing best practices
└── examples/
    ├── agents/
    │   ├── reader.md                     # Example agent: document section extractor
    │   ├── analyzer.md                   # Example agent: technical findings generator
    │   └── report-writer.md              # Example agent: executive report author
    ├── input/
    │   └── architecture.md               # Example input: payment service architecture doc
    └── output/
        ├── plan.md                       # Example orchestration plan (generated)
        └── final_report.md               # Example final deliverable (generated)
```

---

## Writing agent definitions

The orchestrator is **agent-definition-agnostic** — it works with any `.md`
files it finds in the agents directory. For best results, use the recommended
frontmatter format:

```markdown
---
name: my-agent
role: One-line description of what the agent does
input: What the agent expects (format + content)
output: What the agent produces (format + content)
capabilities:
  - capability 1
  - capability 2
---

# My Agent

...instructions...

## Input
...

## Output
...
```

The orchestrator can also infer `name`, `role`, `input`, and `output` from
headings and prose if frontmatter is absent, but explicit frontmatter gives
more reliable agent selection and handoff contract matching.

---

## Worked example

**Task**: Analyse `architecture.md` (a technical design document) and produce
an executive summary report.

**Agent pool**: `examples/agents/` (reader → analyzer → report-writer)

**Pipeline**: Linear — three sequential stages.

```
[T1: reader] ──→ [T2: analyzer] ──→ [T3: report-writer] ──→ final_report.md
```

See `examples/output/plan.md` for the full generated orchestration plan and
`examples/output/final_report.md` for the synthesized deliverable.

---

## Supported pipeline topologies

The skill supports any DAG of agents:

| Pattern | Shape | Example use case |
|---------|-------|-----------------|
| Linear pipeline | A → B → C | Read → analyse → report |
| Fan-out (parallel branches) | A → (B ∥ C ∥ D) | Split document → analyse chunks in parallel |
| Fan-in (merge) | (A ∥ B) → C | Two independent analyses → synthesizer |
| Diamond | A → (B ∥ C) → D | Root context → parallel specialists → merger |
| Map-reduce | A → [B×N] → C | Chunk large doc → process each chunk → summarise |
| Conditional branch | A → B or C | Classifier → domain-specific handler |

See `references/orchestration-patterns.md` for detailed ASCII DAGs, sequencing
rules, and data routing guidance for each topology.
