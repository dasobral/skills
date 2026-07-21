# Agent Definition Conventions

This reference defines the mandatory structural conventions, field formats,
type vocabulary, and style rules for Cursor Markdown and Codex TOML agent
definitions created by the `create-agent` skill.

---

## 1. Platform Selection

Use the platform explicitly requested by the user. Infer a platform only from
unambiguous repository configuration; otherwise ask which target to create.

| Platform | Format | Default location |
|----------|--------|------------------|
| Cursor | Markdown with YAML frontmatter | `./agents/<name>.md` |
| Codex | TOML | `.codex/agents/<name>.toml` |

### Codex TOML

Every Codex definition requires these non-empty string fields:

```toml
name = "agent-name"
description = "One-line discovery description."
developer_instructions = """
You are a focused specialist. Validate the assigned inputs, follow the stated
workflow, return the requested artifact, and report evidence for conclusions.
"""
```

The `name` must match the filename without `.toml`. Put the Role, Inputs,
Process, Output Contract, Constraints, and Integration Hooks content inside
`developer_instructions`. Do not set a model or sandbox policy in a reusable
template; those are deployment decisions.

---

## 2. Cursor Markdown File Layout

Every Cursor agent definition file must follow this exact section order:

```
---
name: {agent-name}
role: {one-line identity}
version: {semver}
---

# {agent-name}

> {role one-liner}

---

## Role
## Inputs
## Process
## Output Contract
## Constraints
## Integration Hooks
```

Sections must not be reordered or omitted. If a section has no content, write
`Not applicable — standalone agent.` rather than removing the heading.

---

## 3. Cursor Front Matter Fields

| Field | Format | Required | Notes |
|-------|--------|----------|-------|
| `name` | `lowercase-kebab-case` | yes | Must match the filename without `.md` |
| `role` | Single sentence, max 120 chars | yes | Used by orchestrators as a human-readable label |
| `version` | `MAJOR.MINOR.PATCH` | yes | Start at `1.0.0`; increment MINOR for backwards-compatible changes, MAJOR for breaking output schema changes |

---

## 4. Naming Conventions

| Item | Convention | Examples |
|------|-----------|---------|
| File name | `lowercase-kebab-case.md` | `document-summarizer.md`, `entity-extractor.md` |
| Agent `name` field | Matches file name without extension | `document-summarizer` |
| Input parameter names | `snake_case` | `document_path`, `max_tokens` |
| Output JSON field names | `snake_case` | `abstract`, `named_entities` |
| Section headings | Title Case, `##` level | `## Output Contract` |

---

For Codex, use the same kebab-case naming rule with a `.toml` extension.

---

## 5. Supported Input/Output Types

Use only types from this vocabulary. Do not invent new types.

| Type token | Description | Example value |
|------------|-------------|---------------|
| `string` | UTF-8 text of arbitrary length | `"hello world"` |
| `integer` | Whole number | `42` |
| `float` | Decimal number | `3.14` |
| `boolean` | True or false | `true` |
| `file_path` | Absolute path to a single file | `"/data/report.md"` |
| `directory_path` | Absolute path to a directory | `"/data/docs/"` |
| `json_object` | A JSON object (`{}`) | `{"key": "value"}` |
| `json_array` | A JSON array (`[]`) | `["a", "b", "c"]` |
| `markdown_text` | Markdown-formatted string | `"## Heading\n..."` |
| `code_snippet` | Source code string with optional language tag | `"def foo(): ..."` |
| `enum(<v1>, <v2>, ...)` | One of a fixed set of string values | `enum(json, markdown, html)` |

**Compound types** — use `json_object` or `json_array` and describe the
internal schema in the field description column or in the Output Contract.

---

## 6. Process Step Rules

Process steps must satisfy all of the following:

1. **Imperative verb first.** Begin each step with an action word:
   `Read`, `Extract`, `Validate`, `Classify`, `Construct`, `Write`,
   `Return`, `Split`, `Merge`, `Filter`, `Sort`, `Invoke`, `Call`.

2. **Reference parameter names directly.** Use backtick notation:
   `Read the file at \`document_path\`` not "read the input file".

3. **Specify branching.** Write explicit `if / otherwise` clauses rather
   than leaving decision logic implicit.

4. **End with output construction.** The last substantive step must produce
   the output artefact defined in Output Contract.

5. **No magic numbers.** Any threshold, limit, or constant used in a step
   (e.g. "exceeds 10,000 tokens") must be either derived from an input
   parameter or defined as a named constant in the step itself.

6. **Count range.** A process must have between 3 and 15 numbered steps.
   Use sub-steps (`a.`, `b.`, `c.`) for branching within a step rather
   than exceeding 15 top-level steps.

---

## 7. Output Contract Rules

- Every agent must declare exactly one `Output type` from this exact vocabulary:
  `json_object`, `markdown_document`, `file_write`, `inline_text`, or `tool_call_sequence`.

- **`json_object`:** Must include a complete JSON Schema block and at least
  one example output. The `"required"` array must list all fields the
  caller can rely on being present.

- **`markdown_document`:** Must include a table of required section headings
  with a description of what each section contains.

- **`file_write`:** Must specify the target path pattern (using input
  parameter names as placeholders), the file format, and the overwrite
  behaviour.

- **`inline_text`:** Describe the structure of the text (e.g.
  "Numbered list of findings, one per line, prefixed with severity tag").

- **`tool_call_sequence`:** List the tools in order, the arguments passed
  to each, and the expected side effects.

---

## 8. Constraint Rules

- Every agent must have at least **2 DO** rules and at least **2 DO NOT** rules.
- DO rules must be positive imperatives: "DO validate …", "DO cite …".
- DO NOT rules must be negative imperatives: "DO NOT modify …", "DO NOT infer …".
- DO NOT repeat the same constraint in both lists (e.g. do not write both
  "DO write to output_path only" and "DO NOT write to any other path" —
  pick the clearer form).
- The following constraints apply to **every agent** and need not be listed
  explicitly (they are assumed):
  - Validate required inputs before beginning.
  - Return a well-formed error object `{"error": "…", "message": "…"}` for
    any unrecoverable failure.
  - Never emit partial output.

---

## 9. Integration Hooks — Mandatory Fields

All six fields in the Integration Hooks table are mandatory. If an agent is
standalone (no orchestrator), write `standalone — not applicable` for
upstream/downstream fields and `not applicable` for parallelism.

| Field | Allowed values / format |
|-------|------------------------|
| `Invocation pattern` | Free text describing how the parent spawns this agent |
| `Upstream dependency` | Agent name(s) or `None — entry point` |
| `Downstream consumers` | Agent name(s), skill name(s), or `None — terminal agent` |
| `Parallelism` | `Yes — embarrassingly parallel`, `Yes — N instances max`, `No — sequential`, or `Conditional — <condition>` |
| `Error contract` | What the caller must do when this agent returns an error object |

---

## 10. Versioning Policy

| Change type | Version bump | Example |
|-------------|--------------|---------|
| Add optional input parameter | MINOR | `1.0.0` → `1.1.0` |
| Add required input parameter | MAJOR | `1.0.0` → `2.0.0` |
| Add optional output field | MINOR | `1.0.0` → `1.1.0` |
| Remove output field | MAJOR | `1.0.0` → `2.0.0` |
| Change output field type | MAJOR | `1.0.0` → `2.0.0` |
| Fix process step (no schema change) | PATCH | `1.0.0` → `1.0.1` |

---

## 11. File Placement

| Context | Path |
|---------|------|
| Cursor inside a skill | `<skill-root>/agents/{agent-name}.md` |
| Cursor standalone system | `./agents/{agent-name}.md` |
| Cursor shared library | `<repo-root>/shared-agents/{agent-name}.md` |
| Codex project agent | `<repo-root>/.codex/agents/{agent-name}.toml` |
| Codex user agent | `~/.codex/agents/{agent-name}.toml` |

Orchestrators reference agents by their relative path from the skill root.
Example in a SKILL.md orchestration step:

```
Read the agent definition from:
<skill_base_path>/agents/summarizer.md
Then invoke it via the Agent tool with the following inputs: ...
```

---

## 12. Style Rules

- Write all prose in the **second person** directed at the agent:
  "You are …", "You receive …", "You produce …".
- Use **bold** for emphasis within prose. Avoid italics.
- Use backtick notation for all parameter names, file paths, and JSON field
  names, even in prose: "the value of `document_path`".
- Do not use emoji in agent definition files.
- Keep line length ≤ 100 characters in prose sections.
- Tables must have header rows and separator rows (standard Markdown GFM).
