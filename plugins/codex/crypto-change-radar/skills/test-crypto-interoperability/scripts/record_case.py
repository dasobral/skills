#!/usr/bin/env python3
"""Canonicalize and hash a cryptographic interoperability case."""

from __future__ import annotations

import hashlib
import json
import sys

from contract_utils import reject_credentials, validate_contract


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def build_record(candidate: dict[str, object]) -> dict[str, object]:
    record = dict(candidate)
    reject_credentials(record)
    record.pop("record_hash", None)
    record["implementations"] = sorted(
        record["implementations"], key=lambda item: (item["name"], item["version"])
    )
    record["negative_tests"] = sorted(
        record["negative_tests"], key=lambda item: item["name"]
    )
    record["evidence_hashes"] = sorted(set(record["evidence_hashes"]))
    record["record_hash"] = f"sha256:{hashlib.sha256(_canonical(record)).hexdigest()}"
    validate_contract(record, "interoperability-case.schema.json")
    return record


def main() -> None:
    try:
        candidate = json.load(sys.stdin)
        if not isinstance(candidate, dict):
            raise ValueError("input must be a JSON object")
        record = build_record(candidate)
        json.dump(record, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
