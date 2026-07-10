# Agent Platform

Workflows for defining focused agents and coordinating evidence-bearing multi-agent tasks.

## Daily workflow

1. Use `create-agent` to define one bounded role, input contract, output type, and constraints.
2. Validate the generated TOML or Markdown definition for the target platform.
3. Use `orchestrate` to build a dependency graph and route explicit artifacts.
4. Review each agent result before composing the final report.

## Triggers

Use when a task benefits from role separation, parallel analysis, repeatable agent definitions, or a traceable orchestration plan.

## Required inputs

- Goal, platform, repository instructions, and allowed tools.
- Role boundaries, dependencies, expected output types, and acceptance criteria.
- Source artifacts each role may read and destinations it may write.

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
