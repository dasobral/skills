#!/usr/bin/env python3
"""Deterministically validate objective scientific run-record requirements."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError
except ModuleNotFoundError:
    Draft202012Validator = None  # type: ignore[assignment,misc]
    ValidationError = ValueError  # type: ignore[assignment,misc]


SCHEMAS = {
    "run-record": "run-record.schema.json",
    "unit-registry": "unit-registry.schema.json",
    "numerical-equivalence-result": "numerical-equivalence-result.schema.json",
    "uncertainty-statement": "uncertainty-statement.schema.json",
}
REFERENCES = Path(__file__).parents[1] / "references"
DEPENDENCY_GUIDANCE = (
    "evidence-gap: Draft 2020-12 validation unavailable; install jsonschema "
    "(for example: python3 -m pip install jsonschema) and rerun."
)


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _format_path(parts: Any) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _schema_errors(instance: Any, schema_name: str) -> list[str]:
    if Draft202012Validator is None:
        return [DEPENDENCY_GUIDANCE]
    schema = json.loads(
        (REFERENCES / SCHEMAS[schema_name]).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    return sorted(
        {
            f"{_format_path(error.absolute_path)}: {error.message}"
            for error in validator.iter_errors(instance)
        }
    )


def canonical_run_id(record: dict[str, Any]) -> str:
    content = {key: value for key, value in record.items() if key != "run_id"}
    canonical = json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"run-sha256:{hashlib.sha256(canonical).hexdigest()}"


def _non_finite_paths(value: Any, path: str = "$") -> list[str]:
    if isinstance(value, float) and not math.isfinite(value):
        return [path]
    if isinstance(value, str) and value.strip().lower() in {
        "nan",
        "+nan",
        "-nan",
        "inf",
        "+inf",
        "-inf",
        "infinity",
        "+infinity",
        "-infinity",
    }:
        return [path]
    if isinstance(value, dict):
        return [
            found
            for key in sorted(value)
            for found in _non_finite_paths(value[key], f"{path}.{key}")
        ]
    if isinstance(value, list):
        return [
            found
            for index, item in enumerate(value)
            for found in _non_finite_paths(item, f"{path}[{index}]")
        ]
    return []


def validate(record: Any, schema_name: str = "run-record") -> list[str]:
    errors = _schema_errors(record, schema_name)
    if schema_name == "run-record":
        if (
            isinstance(record, dict)
            and isinstance(record.get("run_id"), str)
            and record["run_id"] != canonical_run_id(record)
        ):
            errors.append("$.run_id: run_id content hash mismatch")
        for path in _non_finite_paths(
            record.get("results", {}) if isinstance(record, dict) else {},
            "$.results",
        ):
            errors.append(f"{path}: non-finite result")
    if schema_name == "uncertainty-statement" and isinstance(record, dict):
        interval = record.get("interval")
        if (
            isinstance(interval, list)
            and len(interval) == 2
            and all(isinstance(value, (int, float)) for value in interval)
            and interval[0] > interval[1]
        ):
            errors.append("$.interval: lower bound exceeds upper bound")
    return sorted(set(errors))


def main() -> int:
    if Draft202012Validator is None:
        print(
            json.dumps(
                {"errors": [DEPENDENCY_GUIDANCE], "status": "evidence-gap"},
                sort_keys=True,
            )
        )
        return 1
    args = sys.argv[1:]
    schema_name = "run-record"
    if len(args) == 3 and args[0] == "--schema":
        schema_name, input_path = args[1], args[2]
    elif len(args) == 1:
        input_path = args[0]
    else:
        schema_name, input_path = "", ""
    if schema_name not in SCHEMAS or not input_path:
        errors = [
            "usage: validate_run_record.py "
            "[--schema run-record|unit-registry|numerical-equivalence-result|"
            "uncertainty-statement] <artifact.json>"
        ]
    else:
        try:
            record = json.loads(
                Path(input_path).read_text(encoding="utf-8"),
                parse_constant=_reject_constant,
            )
            errors = validate(record, schema_name)
        except (
            OSError,
            UnicodeError,
            ValueError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            errors = [f"input: {exc}"]
    print(
        json.dumps(
            {"errors": errors, "status": "invalid" if errors else "valid"},
            sort_keys=True,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
