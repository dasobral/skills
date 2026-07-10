#!/usr/bin/env python3
"""Create a deterministic entropy qualification evidence record."""

from __future__ import annotations

import hashlib
import json
import sys

from contract_utils import reject_credentials, validate_contract
from derive_health_tests import derive

LIMITATION = (
    "This evidence record does not certify entropy adequacy, quantum origin, "
    "or FIPS status."
)


def _hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        reject_credentials(payload)
        source = payload["source_identity"]
        validate_contract(source, "entropy-source.schema.json")
        health = payload["health_test_parameters"]
        expected = derive(
            {
                "alpha": health["alpha"],
                "alphabet_size": source["alphabet_size"],
                "claimed_min_entropy_bits_per_sample": source[
                    "claimed_min_entropy_bits_per_sample"
                ],
                "adaptive_proportion_window": health[
                    "adaptive_proportion_window"
                ],
            }
        )
        if health != expected:
            raise ValueError(
                "health-test parameters do not match derived SP 800-90B parameters"
            )
        observations = payload["observations"]
        observed_min_entropy = observations.get(
            "estimator_min_entropy_bits_per_sample", 0
        )
        if not isinstance(observed_min_entropy, (int, float)) or isinstance(
            observed_min_entropy, bool
        ):
            raise ValueError("observed estimator min-entropy must be numeric")
        observed_states = [
            observations.get("restart_test", "evidence-gap"),
            observations.get("health_tests", "evidence-gap"),
        ]
        if observed_min_entropy < source["claimed_min_entropy_bits_per_sample"]:
            observed_states.append("fail")
        evidence_state = (
            "fail"
            if "fail" in observed_states
            else "evidence-gap"
            if "evidence-gap" in observed_states
            else "unknown"
            if "unknown" in observed_states
            else "pass"
        )
        result = {
            "schema_version": "1.0",
            "source_id": source["source_id"],
            "source_identity_hash": _hash(source),
            "restart_matrix_identity": payload["restart_matrix_identity"],
            "estimator_versions": sorted(set(payload["estimator_versions"])),
            "estimator_invocations": payload["estimator_invocations"],
            "health_test_parameters": health,
            "claimed_min_entropy_bits_per_sample": source[
                "claimed_min_entropy_bits_per_sample"
            ],
            "observed_min_entropy_bits_per_sample": observed_min_entropy,
            "observations": {
                "restart_test": observed_states[0],
                "health_tests": observed_states[1],
            },
            "artifact_hashes": sorted(set(payload["artifact_hashes"])),
            "evidence_state": evidence_state,
            "decision": "review-required",
            "limitations": [LIMITATION],
        }
        validate_contract(result, "qualification-run.schema.json")
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
