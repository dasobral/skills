---
name: review-crypto-delta
description: Compare two CBOM records and report deterministic semantic cryptographic changes with evidence hashes.
---

# Review Crypto Delta

1. Read `references/authoritative-sources.md` and `references/cbom-delta.schema.json`.
2. Compare assets by stable `asset_id`, not source-line churn.
3. Run `python3 scripts/semantic_diff.py < comparison.json > delta.json`.
4. Review changes to algorithm, parameters, mode, protocol, provider boundary, key purpose, fallback, owner, confidence, and evidence hash.
5. Preserve `evidence-gap` when either side lacks evidence.

Evidence states are exactly `pass`, `fail`, `unknown`, `not-applicable`, and `evidence-gap`; confidence remains `high`, `medium`, or `low`. Evidence state is not a review decision.

Never request secrets or raw production key material. This semantic delta is review evidence and does not certify FIPS status, compliance, security, or migration readiness.
