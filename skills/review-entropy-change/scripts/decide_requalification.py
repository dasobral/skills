#!/usr/bin/env python3
"""Classify entropy-source changes using conservative boundary rules."""

from __future__ import annotations

import json
import sys
from typing import Any

from contract_utils import reject_credentials, validate_contract


BOUNDARY_FIELDS = {
    "source_physics",
    "raw_sampling_point",
    "digitization",
    "conditioning",
    "hardware_identity",
    "firmware_identity",
    "driver_identity",
    "sampling_rate_hz",
    "operating_envelope",
}
LIMITATION = (
    "This workflow records a change-control decision; it does not certify "
    "entropy adequacy, quantum origin, or FIPS status."
)


def main() -> None:
    try:
        payload: dict[str, Any] = json.load(sys.stdin)
        reject_credentials(payload)
        before = payload["before"]
        after = payload["after"]
        fields = sorted(set(before) | set(after))
        changed = [field for field in fields if before.get(field) != after.get(field)]
        policy = payload.get("exception_policy")
        revision = policy.get("revision") if isinstance(policy, dict) else None
        exceptions = set()
        if isinstance(revision, str) and revision.strip():
            for exception in policy.get("exceptions", []):
                field = exception.get("field")
                if (
                    field in BOUNDARY_FIELDS
                    and exception.get("before") == before.get(field)
                    and exception.get("after") == after.get(field)
                ):
                    exceptions.add(field)
        material = sorted((set(changed) & BOUNDARY_FIELDS) - exceptions)
        if material:
            decision = "requalification-required"
            reasons = [
                f"{field} changed and no explicit version-pinned exception policy was supplied"
                for field in material
            ]
        elif changed:
            decision = "review-required"
            reasons = [
                "changed fields require review; exact pinned exceptions do not establish qualification"
            ]
        else:
            decision = "no-material-change"
            reasons = ["no compared fields changed"]
        result = {
            "schema_version": "1.0",
            "source_id": after.get("source_id", before.get("source_id", "unknown")),
            "evidence_state": "pass",
            "decision": decision,
            "changed_fields": changed,
            "reasons": reasons,
            "policy_revision": revision if isinstance(revision, str) else None,
            "limitations": [LIMITATION],
        }
        validate_contract(result, "requalification-decision.schema.json")
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
