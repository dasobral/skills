# Agent Platform

Workflows for defining focused agents and coordinating evidence-bearing multi-agent tasks.

## Daily workflow

1. Use `agent-ste` to rewrite vague goals into explicit, checkable instruction blocks before planning.
2. Use `create-agent` to define one bounded role, input contract, output type, and constraints.
3. Validate the generated TOML or Markdown definition for the target platform.
4. Use `orchestrate` to build a dependency graph and route explicit artifacts.
5. Review each agent result before composing the final report.

## Triggers

Use when a task benefits from role separation, parallel analysis, repeatable agent definitions, or a traceable orchestration plan. Use `agent-ste` when prompts contain vague verbs, missing success criteria, or cross-model handoffs that must stay reproducible.

## Required inputs

- Goal, platform, repository instructions, and allowed tools.
- Role boundaries, dependencies, expected output types, and acceptance criteria.
- Source artifacts each role may read and destinations it may write.
- For `agent-ste`: actor, object, inputs, outputs, success/failure predicates, and scope fences.

## Artifacts

- Agent definitions with explicit contracts.
- Task graph, routed intermediate artifacts, and final synthesis.
- Evidence references, unresolved questions, and failure states.

## Agent authority

Reader, analyzer, orchestrator, and report-writer templates operate only within delegated roles. They cannot grant permissions, approve their own output, or install agent templates automatically.

## Deterministic checks and agent decisions

TOML/Markdown parsing, dependency validation, file existence, and schema checks are deterministic. Task decomposition, role selection, analysis, and synthesis remain agent decisions.

## Data guarantees

Workflows require explicit artifact routing and prohibit invented quotations or evidence. No hook runs for this plugin.

## Limitations and non-claims

This plugin does not guarantee agent isolation, complete analysis, correct orchestration, or conflict-free concurrent writes. The caller remains responsible for permissions and final review.
