---
name: plan-pqc-migration
description: Rank cryptographic assets for post-quantum migration using explicit, reproducible lifecycle and dependency factors.
---

# Plan PQC Migration

1. Read `references/authoritative-sources.md` and pin the policy revision used.
2. Collect confidentiality lifetime, system lifetime, updateability, exposure, migration lead time, and dependencies.
3. Run `python3 scripts/rank_assets.py < assets.json > queue.json`.
4. Review ties and assumptions with asset owners; the numeric score prioritizes review and is not a risk certification.
5. Record unavailable evidence as `evidence-gap`.

Evidence states are exactly `pass`, `fail`, `unknown`, `not-applicable`, and `evidence-gap`; they remain separate from prioritization and migration decisions.

Use only metadata; never collect secrets or raw production key material. This workflow does not certify FIPS status, compliance, quantum safety, interoperability, or implementation correctness.
