---
name: create-agent
description: >
  Scaffolds a new Claude agent definition file (.md) for use inside a skill's
  agents/ directory or as a standalone component in a multi-agent system.
  Guides the user through six definition layers — Role, Inputs, Process,
  Output contract, Constraints, and Integration hooks — then writes a complete,
  ready-to-use {agent-name}.md file.
  TRIGGER when the user asks to "create an agent", "scaffold an agent",
  "define a new agent", "add an agent to my skill", "write an agent definition",
  "build an agent", or similar.
  ALSO TRIGGER via /create-agent slash command.
  ALSO TRIGGER when the user describes an agent they want to build and asks
  for help structuring or formalising it.
allowed-tools: Read, Write, Bash, Glob
---

# Agent Creator Skill

Scaffold a complete Claude agent definition file by guiding the user through
six structured definition layers. The output is a **`{agent-name}.md`** file
— ready to be placed in a skill's `agents/` directory or used as a standalone
component in a multi-agent pipeline.

---

## Step 1 — Resolve Agent Name and Output Path

Determine the agent name and target directory, in order of precedence:

1. **Inline argument** — `/create-agent <agent-name>` or
   `/create-agent <agent-name> <output-dir>` uses those values directly.
2. **User-supplied name in conversation** — extract the agent name from the
   user's description (e.g. "create a summarizer agent" → `summarizer`).
3. **Interactive** — if no name can be inferred, ask:
   > "What should this agent be named? (Use lowercase-kebab-case,
   > e.g. `document-summarizer`)"

Normalise the name to `lowercase-kebab-case`.

Determine the output directory:
- If a `<skill_base_path>/agents/` directory exists in the current working
  tree, default to writing there.
- Otherwise default to `./agents/`.
- If the user specified a path explicitly, use that path.

Announce the resolved target before continuing:
> "Scaffolding agent: `{agent-name}` → `{output-dir}/{agent-name}.md`"

---

## Step 2 — Load the Agent Conventions Reference

Read the conventions guide from:

```
<skill_base_path>/references/agent-conventions.md
```

Keep it in context for the remainder of the skill. It defines mandatory
section headings, field formats, type vocabulary, and style rules.

---

## Step 3 — Gather: Role

Collect or infer the agent's **Role** — its identity, purpose, and
behavioural tone.

If the user has already described the agent in the conversation, extract:

| Field | What to capture |
|-------|----------------|
| **Identity** | One sentence: "You are a …" |
| **Purpose** | What problem does this agent solve? What is its primary job? |
| **Tone** | Analytical / creative / concise / verbose / neutral / domain-expert / etc. |
| **Scope** | What is explicitly in scope? What is out of scope? |

If any field is missing, ask for it directly before proceeding:
> "What is the agent's primary purpose and behavioural tone?"

Write the Role definition to a working scratch buffer — do not output the
final file yet.

---

## Step 4 — Gather: Inputs

Collect the agent's **explicit input parameters**.

For each parameter, capture:

| Attribute | Format |
|-----------|--------|
| `name` | snake_case identifier |
| `type` | one of: `string`, `integer`, `float`, `boolean`, `file_path`, `directory_path`, `json_object`, `json_array`, `markdown_text`, `code_snippet`, `enum(<values>)` |
| `required` | `true` or `false` |
| `description` | one sentence explaining what the value represents |

If the user has described inputs in the conversation, extract them and confirm.
If inputs are vague or missing, ask:
> "What inputs will this agent receive? List each parameter with its name,
> type (e.g. file_path, string, json_object), and whether it is required."

Minimum: every agent must have at least one input parameter. If none are
forthcoming, prompt again before proceeding.

---

## Step 5 — Gather: Process

Collect the agent's **step-by-step reasoning procedure**.

A process is a numbered list of concrete actions the agent takes — not
abstract goals. Each step should be specific enough that another agent (or
a human) could execute it without ambiguity.

Guidelines for well-formed steps:
- Start with an imperative verb: "Read …", "Extract …", "Validate …",
  "Classify …", "Construct …", "Write …"
- Reference input parameter names directly: "Read the file at `{{document_path}}`"
- Specify sub-steps where branching occurs: "If the document exceeds 10,000
  tokens, chunk it into 2,000-token windows with 200-token overlap."
- End with a step that produces the output artefact.

If the user provided a description, synthesise it into numbered steps (minimum
3, maximum 15). Confirm the synthesised steps with the user before proceeding:
> "Here is the proposed process. Does this look correct, or should any steps
> be adjusted?"

---

## Step 6 — Gather: Output Contract

Collect the agent's **exact output format specification**.

Determine the output type:

| Type | When to use |
|------|-------------|
| `json_object` | Structured data consumed by another agent or a parent skill |
| `markdown_document` | Human-readable report or summary |
| `file_write` | Agent writes a file to disk at a specified path |
| `inline_text` | Free-form text printed to the conversation |
| `tool_call_sequence` | Agent emits a sequence of tool calls |

For `json_object` output: define the full JSON schema (field names, types,
required fields, example values).

For `markdown_document` output: define the required section headings and what
each section must contain.

For `file_write` output: specify the target path pattern and file format.

If the output type is ambiguous, ask:
> "What should the agent produce? A JSON object, a markdown report, a written
> file, or something else? If JSON, what fields does it contain?"

---

## Step 7 — Gather: Constraints

Collect explicit **DO / DO NOT rules** for the agent.

Seed the constraints list with sensible defaults based on the role and process
gathered so far, then invite the user to add or remove constraints:

Default seeds (adapt to context):
- DO cite source locations (file path + line number) for every factual claim.
- DO validate all required inputs before beginning the process.
- DO NOT modify files outside the explicitly specified output path.
- DO NOT hallucinate content that cannot be derived from the provided inputs.
- DO NOT truncate output — emit the complete artefact even if it is long.

Ask:
> "Are there any additional DO / DO NOT constraints to add? Any of these
> defaults to remove?"

Finalise the list before proceeding.

---

## Step 8 — Gather: Integration Hooks

Collect how this agent is **invoked by an orchestrator or parent skill**.

Capture:

| Field | What to capture |
|-------|----------------|
| **Invocation pattern** | How does the parent call this agent? (e.g. spawned via Agent tool, included as a system-prompt module, called with explicit `<inputs>` block) |
| **Upstream dependency** | What must complete before this agent runs? (e.g. "requires document-fetcher to complete") |
| **Downstream consumers** | What consumes this agent's output? (e.g. "output passed to ranker agent") |
| **Parallelism** | Can this agent run in parallel with other agents? Under what conditions? |
| **Error contract** | What should the caller do if this agent fails or returns empty output? |

If the agent is standalone (no orchestrator yet), mark all fields as
`standalone — no integration defined` and note that the user can fill them in
later.

---

## Step 9 — Load the Agent Definition Template

Read the output template from:

```
<skill_base_path>/templates/agent-definition.md
```

Replace all `{{PLACEHOLDER}}` tokens with the values collected in Steps 3–8.
The template enforces the canonical section ordering and heading format.

---

## Step 10 — Write the Agent File

Write the completed agent definition to `{output-dir}/{agent-name}.md`.

After writing, print a diff-style preview of the file (full content) in the
conversation so the user can review it inline before committing:

```
--- /dev/null
+++ {output-dir}/{agent-name}.md
```

Then print:
> "File written. Review the definition above and run `/create-agent` again
> with corrections if needed."

---

## Step 11 — Confirm

Print a concise summary:

```
Agent scaffolded successfully.

Name        : {agent-name}
Written to  : {output-dir}/{agent-name}.md
Role        : {one-line identity}
Inputs      : {N} parameter(s) — {comma-separated names}
Process     : {N} steps
Output      : {output-type}
Constraints : {N} rules

Next steps:
  • Place the file in your skill's agents/ directory.
  • Reference it from your skill's SKILL.md orchestration steps.
  • Run /create-agent <next-agent-name> to scaffold additional agents.
```

---

## Skill Rules

- **Complete definitions only.** Do not write the agent file until all six
  layers (Role, Inputs, Process, Output contract, Constraints, Integration
  hooks) have been collected or explicitly marked standalone.
- **Infer before asking.** Extract as much as possible from the user's
  description. Only ask clarifying questions for genuinely missing information.
- **Concrete steps.** Process steps must be imperative and reference input
  parameter names directly. Reject vague steps like "analyse the content" and
  prompt for specifics.
- **Type discipline.** Input and output types must come from the defined type
  vocabulary in the conventions reference. Do not invent new types.
- **Kebab-case filenames.** Agent file names are always `lowercase-kebab-case.md`.
- **One agent per file.** Each `.md` file defines exactly one agent. Do not
  merge multiple agents into a single file.
- **Dual-mode operation.** This skill works as a Claude Code slash command
  (`/create-agent`) and as a chatbot system prompt module. In chatbot mode,
  collect all six layers conversationally before writing the file.

---

## Chatbot System Prompt Module

When embedding this skill as a system prompt module rather than a slash
command, prepend the following block to the system prompt:

```
You are an agent architect. When the user asks you to create an agent,
guide them through six definition layers in order:

  1. Role        — identity, purpose, and behavioural tone
  2. Inputs      — explicit parameters with name, type, and description
  3. Process     — numbered imperative steps referencing input parameter names
  4. Output      — exact format (JSON schema, markdown structure, or file path)
  5. Constraints — explicit DO and DO NOT rules
  6. Integration — invocation pattern, upstream deps, downstream consumers

After collecting all six layers, produce a complete agent definition in this
canonical format:

---
name: {agent-name}
role: {one-line identity}
---

## Role
{identity, purpose, tone, scope}

## Inputs
| Parameter | Type | Required | Description |
...

## Process
1. {step}
2. {step}
...

## Output Contract
{output type and full schema or structure}

## Constraints
**DO**
- ...

**DO NOT**
- ...

## Integration Hooks
| Field | Value |
...

Do not skip layers. Infer from context where possible; ask only when a
layer is genuinely ambiguous or missing.
```
