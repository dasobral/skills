#!/usr/bin/env python3
"""Normalize a focused CBOM while refusing secret-bearing fields."""

from __future__ import annotations

import json
import sys

from contract_utils import reject_credentials, validate_contract


def main() -> None:
    try:
        candidate = json.load(sys.stdin)
        if not isinstance(candidate, dict):
            raise ValueError("input must be a JSON object")
        reject_credentials(candidate)
        runtime = candidate.get("runtime_observation", {})
        if runtime.get("collected") and not runtime.get("authorized"):
            raise ValueError("runtime observation requires explicit authorization")
        candidate["assets"] = sorted(
            candidate.get("assets", []), key=lambda asset: asset["asset_id"]
        )
        validate_contract(candidate, "cbom.schema.json")
        json.dump(candidate, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
