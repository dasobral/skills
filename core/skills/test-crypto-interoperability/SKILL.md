---
name: test-crypto-interoperability
description: Record reproducible cryptographic interoperability cases, including negotiation, fallback, sizes, latency, fragmentation, and negative tests.
---

# Test Crypto Interoperability

1. Read `references/authoritative-sources.md` and `references/interoperability-case.schema.json`.
2. Use isolated non-production test keys and exact implementation versions.
3. Record protocol and draft revision, codepoint or OID, expected fallback, negotiated result, sizes, latency, fragmentation, and negative tests.
4. Include a safe reproduction command and artifact hashes.
5. Run `python3 scripts/run_case.py < run.json > run-record.json` only with an executable path/hash policy, `isolated-temporary-directory` workdir policy, `bubblewrap-full-isolation` sandbox profile, and hash-pinned approved fixture inputs. The runner requires Bubblewrap mount/PID/network isolation and starts from an empty root containing only a read-only `/usr` runtime, isolated `/tmp` and `/work`, read-only fixture binds, and temporary `/output`; it does not expose host `/`, `/etc`, `/home`, `/workspace`, or the project. It clears the environment, never uses a shell or unshare-only fallback, and returns `evidence-gap` without executing when Bubblewrap cannot enforce the profile. Use `record_case.py` for record-only imports.

Runner provenance includes exact argument vector, timeout, exit code, and output hashes; never put credentials in arguments. Evidence states are exactly `pass`, `fail`, `unknown`, `not-applicable`, and `evidence-gap`, separate from interoperability conclusions.

Never collect secrets or raw production key material. A passing case is scoped evidence and does not certify FIPS status, compliance, protocol conformance, security, or broad interoperability.
