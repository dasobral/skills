---
name: challenge-sciml-model
description: Challenge SciML evidence for leakage, physical constraints, extrapolation, uncertainty, baselines, and cost.
license: MIT
metadata:
  plugin: scientific-claim-ledger
  version: "0.1.0"
---

# Challenge SciML Model

Use `references/sciml-challenge-result.schema.json` to record every check.

## Required challenges

- Grouped, temporal, spatial, and regime-aware splits
- Preprocessing and calibration leakage
- Extrapolation beyond observed regimes
- Conservation, invariance, positivity, and boundary conditions
- Residual error versus solution and quantity-of-interest error
- Uncertainty coverage and sharpness
- Seed and initialization sensitivity
- Strong baselines compared at matched error
- End-to-end training, inference, hardware, memory, and energy cost

## Workflow

1. Pin datasets, split identities, preprocessing state, model revision, seeds,
   hardware, and evaluation commands.
2. Record each evidence check as `pass`, `fail`, `unknown`, `not-applicable`,
   or `evidence-gap`, with evidence and rationale. Keep these evidence states
   separate from `block`, `review-required`, and other workflow decisions.
3. Keep objective contract failures distinct from model-adequacy findings.
4. Run `python3 scripts/check_sciml_challenge.py <challenge-result.json>`.
5. Block only forbidden calibration/validation overlap or declared objective
   constraint failures. Escalate model adequacy as `review-required`.

## Rules

- Never hide failed seeds or regimes in aggregate metrics.
- Never compare cost or accuracy at unmatched error targets.
- Agents may challenge and summarize evidence but cannot make the final pass
  decision.
