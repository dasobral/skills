---
name: orchestrate
description: >
  Top-level orchestrator that deploys specialized agents from an agents/
  directory to complete complex tasks. Handles decomposition, task graphs,
  parallel execution via Task tool, artifact routing, failure handling,
  and synthesis. Part of Agent Platform plugin.
  Use when orchestrating agents, running multi-agent pipelines, or
  coordinating parallel subagent work.
---

# Orchestrate

Decompose complex tasks, discover agents, build execution plans, run agents
in correct order, route data between them, and synthesize deliverables.

## Step 1 — Resolve Inputs

Task from user message or argument. Agent pool from `agents/` (or specified path).

## Step 2 — Discover Agents

Glob `agents/**/*.md`. Extract from each: name, role, input/output contracts.

Print Agent Registry table. Halt if empty.

## Step 3 — Decompose Task

Subtasks with IDs (T1, T2...), dependencies, inputs, expected outputs.
Prefer fewer coarse subtasks. Flag gaps where no agent covers a subtask.

## Step 4 — Select Agents

Match by role alignment, input/output compatibility, capability coverage.
Prefer narrowest-scope agent (least authority principle).

## Step 5 — Build Plan

Use `templates/orchestration-plan.md`. Include:
- ASCII task graph (DAG)
- Parallel vs sequential decisions
- Data handoff contracts per edge
- Failure policy (retry, escalate, skip)

Confirm with user unless non-interactive.

## Step 6 — Execute

For parallel subtasks: launch multiple Task tool calls in **one message**.
For sequential: wait for artifacts before next step.

Route outputs as named artifacts between agents per handoff contracts.

## Step 7 — Synthesize

Aggregate agent outputs into final deliverable. Note failures and partial results.

## Modern Execution Patterns

| Pattern | When | How |
|---------|------|-----|
| Parallel explore | Independent research | `subagent_type: explore` × N |
| Parallel review | Module-scoped audits | Custom agents × N, then merge |
| Shell + explore | Diff collection | `subagent_type: shell` + `explore` parallel |
| Cloud agents | Large isolated tasks | Cursor cloud agent per workstream |

## Rules

- Agent-definition-agnostic — work with any `.md` in agents/
- Never assume fixed roster
- Use `references/orchestration-patterns.md` for topology guidance
- Examples in `examples/agents/` and `examples/output/`
