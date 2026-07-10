---
name: audit-scientific-claim
description: Audit claims against hashed evidence while separating verification, validation, and uncertainty quantification.
license: MIT
metadata:
  plugin: scientific-claim-ledger
  version: "0.1.0"
---

# Audit Scientific Claim

Build a claim-to-evidence graph using
`references/claim-evidence-graph.schema.json`.

## Assurance activities

Keep these activities separate; evidence for one does not satisfy another:

1. **Code verification** — was the intended algorithm implemented correctly?
2. **Solution verification** — was the mathematical problem solved accurately?
3. **Model validation** — is the model adequate for the stated context of use?
4. **Uncertainty quantification** — what uncertainty applies to the predicted
   quantity and how was it propagated or calibrated?

Every edge must name its activity, test, run, artifact SHA-256, acceptance
criterion, evidence state, reviewer decision, and decision source. Evidence
state is exactly `pass`, `fail`, `unknown`, `not-applicable`, or
`evidence-gap`; reviewer and workflow decisions use separate vocabularies.

## Workflow

1. Normalize claim wording, scope, context of use, and quantity of interest.
2. Add evidence edges without collapsing the four assurance activities.
3. Mark absent or inapplicable evidence explicitly.
4. Store every referenced artifact below an explicit evidence root using a
   relative path and its SHA-256. Reference each run through its contained
   run-record path and SHA-256; a caller-supplied run ID alone is not evidence.
   The run record must recompute to that `run_id` and its `artifacts` map must
   bind every claim edge's relative path to the same artifact SHA-256. Run
   `python3 scripts/validate_claim_graph.py --evidence-root <directory> <claim-graph.json>`.
   Validation rejects absolute paths, traversal, symlink escape, missing files,
   hash mismatches, modified run records, and artifacts unbound to their run.
5. Route findings to an accountable human reviewer or deterministic acceptance
   check. Agent analysis alone cannot produce an accepted/pass decision.

## Rules

- Do not upgrade correlation, low residual, or benchmark performance into model
  validation.
- Preserve contradictory evidence and rejected edges.
- Do not let the claim auditor make the final pass decision.
