---
name: assess-repository-trust
description: Inventory repository control-plane inputs and produce a private, hash-based trust record before an agent executes repository-supplied automation.
license: MIT
metadata:
  plugin: agentic-trust-gate
  version: "0.1.0"
---

# Assess Repository Trust

Build evidence before granting capabilities. Evidence states describe what was
observed; `allow`, `deny`, and `review-required` are separate policy decisions.
Agents advise; sandbox, permission, policy, and deterministic checks remain the
enforcement boundary.

## Workflow

1. Run `python3 scripts/assess_repository_trust.py <repository> > trust-inventory.json`.
2. For a trust decision, provide every requested capability and hash-bound
   parameter. An approved artifact also requires its exact `--approved-anchor`
   plus `--state-dir` (or `PLUGIN_DATA`).
3. Review the stable repository identity, revision, dirty-state hash, exact
   added/removed/changed capability delta, and prior snapshot hash.
4. Record an explicit decision only with `--policy-id`, `--policy-version`,
   `--approver-id`, `--decision`, and create-only `--anchor-out`. External state
   contains a mode-`0600` HMAC key, anchor, and locked append-only ledger binding
   the complete artifact hash and recomputed decision binding.
   The allow must also be the latest ledger entry for the same repository,
   capabilities, and parameter hashes. Any later allow, deny, revocation, or
   superseding decision invalidates the older anchor.
5. Verify a ledger with
   `python3 scripts/assess_repository_trust.py --verify-ledger STATE_DIR`.
6. Review every `fail`, `unknown`, and `evidence-gap` item before executing hooks,
   lifecycle commands, tasks, MCP servers, or repository binaries.
7. Independently verify requested capabilities against the actual sandbox and
   permission configuration. Never infer trust from an agent's recommendation.
8. Validate a saved artifact with
   `python3 scripts/assess_repository_trust.py --validate trust-inventory.json`.
9. Retain only relative paths and SHA-256 hashes. Parameter values are hashed;
   do not copy file contents,
   credentials, environment values, prompts, or personal data into the artifact.

The inventory covers agent instructions, hooks, skills, MCP configuration,
lifecycle scripts, editor tasks, devcontainers, symlinks, and executables. See
`references/schemas/trust-inventory.schema.json` for the output contract.
Inventories, prior snapshots, and ledger entries use Draft 2020-12 validation
before semantic checks. Missing `jsonschema==4.26.0` yields an `evidence-gap`
with setup guidance.
An unauthenticated, forged, unlinked, or binding-mismatched snapshot can never
produce `allow`.
