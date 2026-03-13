---
name: {{AGENT_NAME}}
role: {{ROLE_ONE_LINE}}
version: 1.0.0
---

<!--
  AGENT DEFINITION TEMPLATE
  ─────────────────────────
  Replace every {{PLACEHOLDER}} with the real value.
  Remove this comment block before committing the file.

  Placement: <skill-root>/agents/{{AGENT_NAME}}.md
  Reference: https://github.com/anthropics/claude-skills (agent-creator skill)
-->

# {{AGENT_NAME}}

> {{ROLE_ONE_LINE}}

---

## Role

**Identity**
{{ROLE_IDENTITY}}
<!-- Example: "You are a document summarizer agent. You receive a single
     document and produce a structured JSON summary." -->

**Purpose**
{{ROLE_PURPOSE}}
<!-- Example: "Extract the key themes, entities, and a one-paragraph abstract
     from any document so downstream agents can process it without re-reading
     the full text." -->

**Tone**
{{ROLE_TONE}}
<!-- Example: "Analytical and concise. Prefer precision over completeness.
     Never speculate beyond what the document states." -->

**Scope**
- In scope: {{SCOPE_IN}}
- Out of scope: {{SCOPE_OUT}}

---

## Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
{{#each INPUTS}}
| `{{name}}` | `{{type}}` | {{required}} | {{description}} |
{{/each}}

<!--
  Supported types:
    string · integer · float · boolean
    file_path · directory_path
    json_object · json_array
    markdown_text · code_snippet
    enum(<value1>, <value2>, ...)

  Example rows:
  | `document_path` | `file_path`  | true  | Absolute path to the document to summarise. |
  | `max_tokens`    | `integer`    | false | Token budget for the summary. Default: 500. |
  | `output_format` | `enum(json, markdown)` | false | Desired output format. Default: json. |
-->

---

## Process

<!--
  Write numbered, imperative steps.
  Reference input parameter names directly using {{param_name}} notation.
  Be specific: another agent must be able to execute this without clarification.
  Minimum 3 steps; maximum 15 steps.
-->

1. Validate that `{{INPUT_PARAM_1}}` {{VALIDATION_CONDITION}}.
   If validation fails, return an error object:
   `{"error": "invalid_input", "message": "<reason>"}` and stop.

2. {{STEP_2}}
   <!-- Example: "Read the file at {{document_path}} using the Read tool." -->

3. {{STEP_3}}
   <!-- Example: "Extract the following fields from the content:
        - title (H1 heading or first sentence)
        - themes (up to 5 key topics, noun phrases)
        - named_entities (people, organisations, locations mentioned ≥ 2×)
        - abstract (≤ 3 sentences summarising the core argument)" -->

4. {{STEP_4}}
   <!-- Add or remove steps as needed -->

5. Construct the output artefact using the schema defined in **Output Contract**.
   Verify every required field is populated before emitting.

<!--
  OPTIONAL STEP PATTERNS:
  ─────────────────────────────────────────────────────────────
  Chunking:
    If {{input_param}} exceeds {{N}} tokens, split into chunks of {{chunk_size}}
    with {{overlap}} token overlap. Process each chunk independently and merge.

  Conditional branching:
    If {{condition}}, execute sub-steps a–c. Otherwise skip to step N.

  Tool calls:
    Use the {{ToolName}} tool with arguments {{arg_description}}.

  Looping:
    For each item in `{{json_array_param}}`, apply steps N–M and collect results.
  ─────────────────────────────────────────────────────────────
-->

---

## Output Contract

**Output type:** `{{OUTPUT_TYPE}}`
<!-- Allowed values: json_object · markdown_document · file_write · inline_text · tool_call_sequence -->

{{#if OUTPUT_TYPE == "json_object"}}
### JSON Schema

```json
{
  "type": "object",
  "required": [{{REQUIRED_FIELDS}}],
  "properties": {
    "{{FIELD_1}}": {
      "type": "{{FIELD_1_TYPE}}",
      "description": "{{FIELD_1_DESCRIPTION}}"
    },
    "{{FIELD_2}}": {
      "type": "{{FIELD_2_TYPE}}",
      "description": "{{FIELD_2_DESCRIPTION}}"
    }
  }
}
```

### Example Output

```json
{
  "{{FIELD_1}}": {{EXAMPLE_VALUE_1}},
  "{{FIELD_2}}": {{EXAMPLE_VALUE_2}}
}
```
{{/if}}

{{#if OUTPUT_TYPE == "markdown_document"}}
### Required Sections

| Section heading | Content |
|-----------------|---------|
| `## {{SECTION_1}}` | {{SECTION_1_DESCRIPTION}} |
| `## {{SECTION_2}}` | {{SECTION_2_DESCRIPTION}} |

### Example Output

```markdown
## {{SECTION_1}}
{{SECTION_1_EXAMPLE}}

## {{SECTION_2}}
{{SECTION_2_EXAMPLE}}
```
{{/if}}

{{#if OUTPUT_TYPE == "file_write"}}
### File Output

- **Path pattern:** `{{FILE_PATH_PATTERN}}`
  <!-- Example: "{output_dir}/{document_name}_summary.json" -->
- **Format:** `{{FILE_FORMAT}}`
- **Overwrite behaviour:** {{OVERWRITE_BEHAVIOUR}}
  <!-- Example: "Overwrite silently" or "Fail with error if file exists" -->
{{/if}}

---

## Constraints

**DO**
- {{DO_RULE_1}}
  <!-- Example: "Cite the exact source location (file path + line number) for every factual claim." -->
- {{DO_RULE_2}}
  <!-- Example: "Validate all required inputs at the start of the Process before taking any other action." -->
- {{DO_RULE_3}}
- Emit the complete output artefact — never truncate.

**DO NOT**
- {{DO_NOT_RULE_1}}
  <!-- Example: "DO NOT modify any file other than the explicitly specified output path." -->
- {{DO_NOT_RULE_2}}
  <!-- Example: "DO NOT hallucinate or infer content that is not present in the provided inputs." -->
- {{DO_NOT_RULE_3}}
- DO NOT emit partial output and indicate "continued" — always produce a
  complete, self-contained artefact in a single response.

---

## Integration Hooks

| Field | Value |
|-------|-------|
| **Invocation pattern** | {{INVOCATION_PATTERN}} |
| **Upstream dependency** | {{UPSTREAM_DEPENDENCY}} |
| **Downstream consumers** | {{DOWNSTREAM_CONSUMERS}} |
| **Parallelism** | {{PARALLELISM}} |
| **Error contract** | {{ERROR_CONTRACT}} |

<!--
  INVOCATION PATTERN examples:
    "Spawned via Agent tool by the parent skill orchestrator with an explicit
     <inputs> block: { document_path, max_tokens }"
    "Included as a system-prompt module; user pastes input into the conversation"

  UPSTREAM DEPENDENCY examples:
    "Requires document-fetcher agent to complete and produce document_path"
    "None — this is the pipeline entry point"

  DOWNSTREAM CONSUMERS examples:
    "Output JSON passed to the ranker agent as its `candidates` input"
    "None — output is returned directly to the user"

  PARALLELISM examples:
    "Can run in parallel with other summarizer instances (one per document)"
    "Must run sequentially — depends on shared state from step N"

  ERROR CONTRACT examples:
    "On failure, return { error: 'agent_failed', message: '<reason>' };
     parent skill should surface the error message to the user and halt"
    "On empty output, parent skill retries once with a reduced max_tokens value"
-->
