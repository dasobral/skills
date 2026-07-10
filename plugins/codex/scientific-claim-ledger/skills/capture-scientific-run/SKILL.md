---
name: capture-scientific-run
description: Capture a replayable scientific run with units, provenance, numerical equivalence, and uncertainty contracts.
license: MIT
metadata:
  plugin: scientific-claim-ledger
  version: "0.1.0"
---

# Capture Scientific Run

Create an immutable run record before interpreting results.

## Workflow

1. State the context of use and quantity of interest.
2. Register every quantity's unit, coordinate frame, and dimensional meaning in
   `references/unit-registry.schema.json`.
3. Record tolerances, uncertainty meaning, and the acceptance threshold.
4. Capture source revision, input SHA-256 hashes, environment, compiler/runtime
   settings, hardware, parallel layout, random seeds, and an exact replay command.
   Use `python3 scripts/capture_run_record.py --help` for deterministic local
   capture. Record unavailable metadata as `evidence-gap`; never invent it.
   The capture command applies the no-secret policy recursively: credential
   fields and values are removed without secret-derived hashes or identifiers;
   only constant markers and affected field names remain. Absolute paths become
   safe relative aliases, and replay/compiler arguments are sanitized.
5. Classify reproducibility as `bitwise`, `numerically-equivalent`, or
   `scientifically-equivalent`. For numerical equivalence, emit
   `references/numerical-equivalence-result.schema.json`.
6. Describe uncertainty with `references/uncertainty-statement.schema.json`;
   never treat an unspecified error bar as uncertainty quantification.
7. Associate each claimable result with the run by passing its contained path
   with `--artifact`; the capture command records that relative path and
   SHA-256 under `artifacts`.
8. Write the run using `references/run-record.schema.json`, then run:
   `python3 scripts/validate_run_record.py <run-record.json>`.
   `run_id` is the canonical SHA-256 of the complete record excluding `run_id`;
   validation recomputes it and rejects modified records.

## Rules

- Hash inputs and result artifacts; do not embed secrets.
- Preserve failed and non-finite runs as evidence, but never mark them accepted.
- Do not infer missing units, frames, seeds, provenance, or uncertainty meaning.
- A tool or agent may validate contract completeness; it cannot make the final
  scientific pass decision.
- Evidence state is exactly one of `pass`, `fail`, `unknown`, `not-applicable`,
  or `evidence-gap`; keep it separate from workflow and reviewer decisions.
