---
name: review-entropy-change
description: Decide whether an entropy-source change requires requalification using deterministic source-boundary rules and pinned exceptions.
---

# Review Entropy Change

1. Read `references/authoritative-sources.md` and `references/requalification-decision.schema.json`.
2. Compare source physics, sampling boundary, digitization, conditioner, hardware, firmware, driver, sampling rate, and operating envelope.
3. Run `python3 scripts/decide_requalification.py < comparison.json > decision.json`.
4. Require requalification for any boundary change unless an explicit version-pinned policy exception identifies the exact field and before/after values.
5. Use `review-required` for other changes and `no-material-change` only when records match.

Evidence states are exactly `pass`, `fail`, `unknown`, `not-applicable`, and `evidence-gap`. They are recorded separately from `requalification-required`, `review-required`, and `no-material-change`.

Never collect secrets or raw production key material. This change-control result does not certify FIPS status, quantum origin, entropy adequacy, compliance, or continued fitness for use.
