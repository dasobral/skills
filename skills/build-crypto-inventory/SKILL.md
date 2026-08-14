---
name: build-crypto-inventory
description: Build a hash-backed cryptographic bill of materials from authorized repository evidence without collecting secrets or raw key material.
---

# Build Crypto Inventory

1. Read `references/authoritative-sources.md` and `references/cbom.schema.json`.
2. Inventory source, dependencies, binaries, configuration, certificates, and only explicitly authorized runtime observations.
3. Run `python3 scripts/collect_evidence.py < requests.json > collection.json` to extract normalized CBOM asset candidates from authorized source, dependency, configuration, binary, and public-certificate files. It rejects every symlink component and sensitive resolved name; missing files produce `evidence-gap`.
4. Record algorithm, parameters, mode, protocol, provider boundary, key purpose, fallback, owner, confidence, evidence state, and evidence hash.
5. Run `python3 scripts/build_inventory.py < candidate.json > cbom.json`; the Draft 2020-12 contract rejects undeclared fields.
6. Report unavailable evidence as `evidence-gap`; never infer it.

For native hooks, register a policy conforming to `references/crypto-policy.schema.json` under external `PLUGIN_DATA/crypto-change-radar` (or the explicit plugin state directory). Approval requires a detached Ed25519 signature verified against the public key selected by `CRYPTO_CHANGE_RADAR_TRUST_ROOT` inside the explicit `CRYPTO_CHANGE_RADAR_TRUST_BOUNDARY`. Trust-path components must be non-symlink, root- or `CRYPTO_CHANGE_RADAR_TRUSTED_UID`-owned, non-writable by group/other, and non-replaceable by the invoking unprivileged process. The signed payload binds plugin, decision, approver identity, timestamp, policy digest, and prior ledger entry. The local HMAC chain is only tamper-evident storage after signature verification; it is not approval authority.

Evidence states are exactly `pass`, `fail`, `unknown`, `not-applicable`, and `evidence-gap`. They describe evidence, never a review or migration decision.

Do not collect, print, hash, or retain secrets, private keys, symmetric key bytes, seed material, tokens, or raw production key material. Certificate metadata and public-key fingerprints are allowed. This workflow produces evidence, does not certify FIPS status, compliance, security, or fitness for use.
