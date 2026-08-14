---
name: review-mcp-drift
description: Compare two MCP capability snapshots canonically and emit deterministic evidence for capability and supply-chain drift.
license: MIT
metadata:
  plugin: agentic-trust-gate
  version: "0.1.0"
---

# Review MCP Drift

Compare evidence, not presentation order. The workflow does not authorize an
MCP server; runtime allowlists, permissions, authentication policy, and sandbox
controls remain independent enforcement.

## Workflow

1. Capture sanitized MCP snapshots. Exclude tokens, environment values, request
   bodies, user content, and credentials.
2. Run
   `python3 scripts/review_mcp_drift.py BEFORE.json AFTER.json > capability-delta.json`.
3. Review the union of canonical tool names. The scanner covers server
   instructions, tool descriptions, schema annotations/defaults, and every remote
   descriptor leaf. Findings contain exact JSON Pointer locations and content
   hashes, never raw instruction text.
4. Treat added/removed capabilities as `review-required`; policy marks destructive
   additions, destructive escalation, scope expansion, auth endpoint changes,
   shadowing, hidden instructions, token passthrough, and remote mutability as
   `deny`/`block`; other remote descriptor drift is `review-required`/`review`.
5. Read `evidence_state` independently from `decision`. A complete observation
   can still produce a deny decision.
6. Validate retained output with
   `python3 scripts/review_mcp_drift.py --validate capability-delta.json`.

Treat `unknown` and `evidence-gap` as unresolved, never as approval. The contract
is `references/schemas/capability-delta.schema.json`.
All input/output artifacts use Draft 2020-12 validation first. Missing
`jsonschema==4.26.0` yields an `evidence-gap` and setup guidance.
