# Crypto Change Radar

Evidence-first cryptographic inventory, semantic change review, PQC planning, and interoperability testing.

## Daily workflow

1. Run `build-crypto-inventory` across authorized source, dependency, binary, configuration, certificate, and runtime evidence.
2. Use `review-crypto-delta` to compare the current CBOM with a pinned baseline.
3. Use `plan-pqc-migration` to rank affected assets and dependencies.
4. Run `test-crypto-interoperability` with pinned implementations, protocol revisions, identifiers, and negative cases.

## Triggers

Use for cryptographic dependency or configuration changes, protocol/provider changes, certificate updates, policy changes, PQC planning, or interoperability regressions. The hook reports changed inventory inputs and explicitly forbidden primitives from checked-in policy.

## Required inputs

- Authorized repository/revision, evidence scope, policy, prior CBOM, and artifact hashes.
- Algorithm, parameter, mode, protocol, provider, key-purpose, fallback, and ownership context.
- Versioned peers, codepoints/OIDs, expected fallback, network constraints, and reproduction commands.

## Artifacts

- CBOM and semantic CBOM delta.
- Prioritized PQC migration queue with dependencies and rationale.
- Interoperability cases and run records covering negotiation, sizes, latency, fragmentation, and negative tests.

## Agent authority

The crypto archaeologist, protocol challenger, and evidence notary collect and challenge evidence. They cannot certify FIPS status, cryptographic security, provider compliance, or migration approval.

## Deterministic checks and agent decisions

Schemas, hashes, policy matches, version comparisons, negotiation results, and test measurements are deterministic. Semantic impact, migration priority, fallback acceptability, and residual risk require expert review.

## Data guarantees

Inventory collection excludes secrets and records source class, confidence, and evidence hashes. Missing optional tools produce an evidence-gap rather than fabricated certainty.

## Limitations and non-claims

This plugin is not a complete secret scanner, penetration test, FIPS validation, cryptographic proof, or guarantee of interoperability outside the pinned test matrix.
