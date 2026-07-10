# Entropy Flight Recorder

Versioned qualification evidence and change review for entropy, RNG, and QRNG sources.

## Daily workflow

1. Use `qualify-entropy-source` to identify the physical source, sampling boundary, digitization, conditioning, implementation, and operating envelope.
2. Capture restart matrices, raw-sample provenance, estimator versions, health-test parameters, and artifact hashes.
3. Use `review-entropy-change` whenever hardware, firmware, conditioner, rate, driver, or envelope changes.
4. Record requalification-required, review-required, or no-material-change with policy-pinned reasons.

## Triggers

Use for new entropy sources, qualification runs, health-test tuning, QRNG integration, implementation changes, operating-envelope changes, or baseline drift. The hook reports missing source identity and changed source-boundary fields.

## Required inputs

- Source physics, adversarial assumptions, raw sampling point, and digitization/conditioning chain.
- Hardware, firmware, driver, sampling rate, environment, restart matrix, and estimator identities.
- Claimed min-entropy, health-test policy, prior baseline, and all evidence hashes.

## Artifacts

- Entropy-source identity and qualification-run records.
- Health-test parameters and entropy baseline.
- Requalification decision with changed fields, policy reference, evidence state, and rationale.

## Agent authority

The entropy analyst, source-physics skeptic, and evidence curator challenge and organize evidence. They cannot certify quantum origin, entropy adequacy, standards compliance, or production approval.

## Deterministic checks and agent decisions

Schema validation, hashes, identity comparison, health-test execution, and policy rules are deterministic. Physical-model adequacy, estimator interpretation, exception acceptance, and qualification approval require qualified review.

## Data guarantees

Records bind claims to source boundary, versions, operating envelope, and artifact hashes. Missing tools or evidence are explicit evidence-gaps, not silent passes.

## Limitations and non-claims

This plugin does not prove randomness, quantum origin, independence, min-entropy, cryptographic suitability, or compliance with any certification program.
