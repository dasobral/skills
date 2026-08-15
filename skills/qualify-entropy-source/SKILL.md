---
name: qualify-entropy-source
description: Capture reproducible entropy-source qualification evidence with source physics, boundaries, estimators, health tests, and artifact hashes.
---

# Qualify Entropy Source

1. Read `references/authoritative-sources.md` and all three JSON schemas.
2. Identify source physics, adversarial assumptions, raw sampling point, digitization, conditioning, hardware, firmware, driver, sampling rate, and operating envelope.
3. Pin restart matrix identity, estimator versions and invocation argument/hash/exit-code provenance, health-test parameters, and artifact hashes.
4. Derive RCT/APT parameters with `python3 scripts/derive_health_tests.py`; record formula version, `0 < alpha < 1`, alphabet size, claimed entropy, and the enforced APT window (`1024` for a binary alphabet, `512` otherwise).
5. Run `python3 scripts/qualify_run.py < input.json > qualification.json`; it recomputes the parameters, rejects mismatches, and records `fail` when observed estimator min-entropy is below the source's claim.
6. Treat missing tools or evidence as `evidence-gap`; require expert review of the resulting evidence.

For native hooks, register a baseline conforming to `references/entropy-baseline.schema.json` under external `PLUGIN_DATA/entropy-flight-recorder` (or the explicit plugin state directory). Approval requires a detached Ed25519 signature verified against the public key selected by `ENTROPY_FLIGHT_RECORDER_TRUST_ROOT` inside the explicit `ENTROPY_FLIGHT_RECORDER_TRUST_BOUNDARY`. Trust-path components must be non-symlink, root- or `ENTROPY_FLIGHT_RECORDER_TRUSTED_UID`-owned, non-writable by group/other, and non-replaceable by the invoking unprivileged process. The signed payload binds plugin, decision, approver identity, timestamp, baseline digest, and prior ledger entry. The local HMAC chain is only tamper-evident storage after signature verification; it is not approval authority.

Evidence states are exactly `pass`, `fail`, `unknown`, `not-applicable`, and `evidence-gap`. Keep them separate from the `review-required` decision.

Use authorized test captures only. Never collect secrets, seed material, raw production key material, or raw production entropy streams. This workflow records evidence and does not certify FIPS status, quantum origin, entropy adequacy, compliance, or fitness for use.
