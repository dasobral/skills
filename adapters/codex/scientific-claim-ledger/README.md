# Scientific Claim Ledger

Reproducible run capture and evidence-linked review for numerical science and scientific machine learning.

## Daily workflow

1. Use `capture-scientific-run` to record context of use, quantity of interest, units, frames, tolerances, uncertainty meaning, environment, seeds, inputs, and replay command.
2. Classify reproducibility as bitwise, numerically equivalent, or scientifically equivalent.
3. Use `audit-scientific-claim` to link each claim to tests, runs, hashes, acceptance criteria, and reviewer decisions.
4. Use `challenge-sciml-model` for leakage, regime, extrapolation, physics, uncertainty, baseline, seed, and cost challenges.

## Triggers

Use for publication or release evidence, changed numerical results, model validation, SciML evaluation, uncertainty claims, calibration changes, or provenance gaps. The hook reports objective schema, unit, finiteness, invariant, and calibration/validation-overlap failures.

## Required inputs

- Source revision, input hashes, environment, compiler/runtime, hardware, parallel layout, seeds, and replay command.
- Quantities, units, coordinate frames, tolerances, uncertainty semantics, and acceptance thresholds.
- Claim text, evidence artifacts, reviewer identity, dataset partitions, baselines, and challenge policy.

## Artifacts

- Run record, unit registry, numerical-equivalence result, and uncertainty statement.
- Claim-to-evidence graph separating code verification, solution verification, model validation, and UQ.
- SciML challenge result with objective failures, review findings, and evidence states.

## Agent authority

The numerical verifier, SciML challenger, and claim auditor inspect evidence and recommend findings. They cannot declare scientific truth, approve claims, alter acceptance criteria, or hide failed invariants.

## Deterministic checks and agent decisions

Schemas, hashes, units, finiteness, declared invariants, split overlap, and evidence references are deterministic checks. Model adequacy, scientific equivalence, uncertainty interpretation, and claim acceptance require accountable review.

## Data guarantees

Artifacts bind claims to immutable evidence and separate deterministic failures from review-only judgments. Capture helpers redact credential fields and absolute paths; missing dependencies become evidence-gaps.

## Limitations and non-claims

This plugin does not prove scientific validity, reproducibility on every platform, model adequacy, uncertainty correctness, peer review, or publication readiness.
