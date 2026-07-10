#!/usr/bin/env python3
"""Rank PQC migration candidates with an explicit deterministic formula."""

from __future__ import annotations

import json
import sys
from typing import Any

from contract_utils import reject_credentials, validate_contract


METHOD = "v1:cl+sl+exposure+lead+(6-updateability)+dependency-count"


def _rank(asset: dict[str, Any]) -> dict[str, Any]:
    dependencies = sorted(set(asset["dependencies"]))
    factors = {
        "confidentiality_lifetime_years": asset["confidentiality_lifetime_years"],
        "system_lifetime_years": asset["system_lifetime_years"],
        "updateability": asset["updateability"],
        "exposure": asset["exposure"],
        "migration_lead_time_years": asset["migration_lead_time_years"],
        "dependency_count": len(dependencies),
    }
    score = (
        factors["confidentiality_lifetime_years"]
        + factors["system_lifetime_years"]
        + factors["exposure"]
        + factors["migration_lead_time_years"]
        + (6 - factors["updateability"])
        + factors["dependency_count"]
    )
    return {
        "asset_id": asset["asset_id"],
        "score": score,
        "evidence_state": "pass",
        "factors": factors,
        "dependencies": dependencies,
    }


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        reject_credentials(payload)
        queue = [_rank(asset) for asset in payload["assets"]]
        queue.sort(key=lambda item: (-item["score"], item["asset_id"]))
        for index, item in enumerate(queue, 1):
            item["rank"] = index
        result = {
            "schema_version": "1.0",
            "policy_revision": payload["policy_revision"],
            "ranking_method": METHOD,
            "queue": queue,
        }
        validate_contract(result, "pqc-queue.schema.json")
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
