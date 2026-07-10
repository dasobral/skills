#!/usr/bin/env python3
"""Produce a deterministic semantic delta between focused CBOM records."""

from __future__ import annotations

import json
import sys
from typing import Any

from contract_utils import reject_credentials, validate_contract


SEMANTIC_FIELDS = (
    "algorithm",
    "parameters",
    "mode",
    "protocol",
    "provider_boundary",
    "key_purpose",
    "fallback",
    "owner",
    "confidence",
    "evidence_hash",
)


def _change(asset_id: str, kind: str, before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    fields = {}
    for field in SEMANTIC_FIELDS:
        old = before.get(field) if before else None
        new = after.get(field) if after else None
        if old != new:
            fields[field] = {"before": old, "after": new}
    confidences = [
        record.get("confidence", "evidence-gap")
        for record in (before, after)
        if record is not None
    ]
    confidence = confidences[0] if confidences and len(set(confidences)) == 1 else "low"
    required_hashes = [
        record.get("evidence_hash")
        for record in (before, after)
        if record is not None
    ]
    return {
        "asset_id": asset_id,
        "change_type": kind,
        "fields": fields,
        "confidence": confidence,
        "evidence_state": "pass" if all(required_hashes) else "evidence-gap",
        "before_evidence_hash": before.get("evidence_hash") if before else None,
        "after_evidence_hash": after.get("evidence_hash") if after else None,
    }


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        reject_credentials(payload)
        before = payload["before"]
        after = payload["after"]
        old_assets = {item["asset_id"]: item for item in before["assets"]}
        new_assets = {item["asset_id"]: item for item in after["assets"]}
        changes = []
        for asset_id in sorted(old_assets.keys() | new_assets.keys()):
            old = old_assets.get(asset_id)
            new = new_assets.get(asset_id)
            kind = "added" if old is None else "removed" if new is None else "modified"
            change = _change(asset_id, kind, old, new)
            evidence_changed = (
                change["before_evidence_hash"] != change["after_evidence_hash"]
            )
            if kind != "modified" or change["fields"] or evidence_changed:
                changes.append(change)
        result = {
            "schema_version": "1.0",
            "before_revision": before["repository"]["revision"],
            "after_revision": after["repository"]["revision"],
            "changes": changes,
        }
        validate_contract(result, "cbom-delta.schema.json")
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
