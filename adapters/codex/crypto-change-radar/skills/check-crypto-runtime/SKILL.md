---
name: check-crypto-runtime
description: Check the optional pinned JSON Schema runtime required by crypto evidence helpers and hooks without installing software.
---

# Check Crypto Runtime

Run `python3 scripts/check_runtime.py`.

The check is read-only and idempotent. It does not install or upgrade packages. If it reports `evidence-gap`, show the setup guidance and obtain user approval before they install `jsonschema==4.26.0`; then rerun the check.

Provision a non-writable Ed25519 public key outside the project. Set `CRYPTO_CHANGE_RADAR_TRUST_BOUNDARY` to its explicit managed boundary, `CRYPTO_CHANGE_RADAR_TRUST_ROOT` to the key within that boundary, and optionally `CRYPTO_CHANGE_RADAR_TRUSTED_UID` for a non-root provisioning owner. Every component from boundary through key must be non-symlink, trusted-owned, non-writable by group/other, and non-replaceable by the invoking user. First run:

`python3 scripts/register_control_state.py --state-dir "$PLUGIN_DATA/crypto-change-radar" --project-root "$PWD" --artifact /trusted/candidate/crypto-policy.json --approver-id ID --signed-at UTC_TIMESTAMP --prepare`

Sign the canonical `signing_payload` externally, then rerun with the same arguments and `--signature SIGNATURE`. Registration never creates a private signing key and refuses missing, writable, or invalid trust roots and signatures with `evidence-gap`. The signed payload binds plugin, approver identity, timestamp, policy digest, decision, and prior entry. A mode-0600 HMAC chain protects local storage only after signature verification.
