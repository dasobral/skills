#!/usr/bin/env python3
"""Constrained replay role worker; never receives workspace or other role inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:
    Draft202012Validator = None

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def _hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _hash_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def main() -> None:
    if Draft202012Validator is None:
        print(
            json.dumps(
                {
                    "valid": False,
                    "evidence_state": "evidence-gap",
                    "setup_guidance": (
                        "Install the pinned validator: "
                        "python -m pip install jsonschema==4.26.0"
                    ),
                },
                sort_keys=True,
            )
        )
        raise SystemExit(2)
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-definition", required=True, type=Path)
    args = parser.parse_args()
    definition_bytes = args.role_definition.read_bytes()
    definition = tomllib.loads(definition_bytes.decode("utf-8"))
    envelope = json.load(sys.stdin)
    schema_path = (
        Path(__file__).parents[1]
        / "references"
        / "schemas"
        / "worker-envelope.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    schema_errors = list(Draft202012Validator(schema).iter_errors(envelope))
    if schema_errors:
        first = min(
            schema_errors,
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        location = "/" + "/".join(str(part) for part in first.absolute_path)
        raise SystemExit(f"worker envelope schema: {location} violates {first.validator}")
    if not isinstance(envelope, dict):
        raise SystemExit("worker envelope must be an object")
    role = definition.get("role")
    if envelope.get("role") != role:
        raise SystemExit("worker role mismatch")
    definition_hash = _hash_bytes(definition_bytes)
    if envelope.get("role_definition_hash") != definition_hash:
        raise SystemExit("worker role definition hash mismatch")
    role_input = envelope.get("role_input")
    if not isinstance(role_input, dict):
        raise SystemExit("worker role_input must be an object")
    allowed_input_keys = set(definition.get("allowed_input_keys", []))
    if set(role_input) - allowed_input_keys:
        raise SystemExit("worker received disallowed role input")
    if envelope.get("other_role_inputs") is not None:
        raise SystemExit("worker must not receive other role inputs")
    actions = envelope.get("planned_actions")
    if not isinstance(actions, list):
        raise SystemExit("worker planned_actions must be a list")
    allowed_tools = set(definition.get("allowed_tools", []))
    requests = []
    for action in actions:
        if (
            not isinstance(action, dict)
            or set(action) != {"tool", "arguments"}
            or action.get("tool") not in allowed_tools
            or not isinstance(action.get("arguments"), dict)
        ):
            raise SystemExit("worker action violates packaged role constraints")
        requests.append(action)
    output: dict[str, object] = {
        "protocol_version": definition.get("protocol_version"),
        "role": role,
        "role_definition_hash": definition_hash,
        "role_input_hash": _hash(role_input),
        "requests": requests,
    }
    monitor_context = envelope.get("monitor_context")
    if definition.get("receives_monitor_context"):
        if not isinstance(monitor_context, dict):
            raise SystemExit("judge requires monitor_context")
        output["assessment"] = {
            "input_hash": _hash(monitor_context),
            "evidence_state": (
                "fail" if monitor_context.get("attack_success") else "pass"
            ),
            "decision": (
                "review-required"
                if monitor_context.get("attack_success")
                else "allow"
            ),
        }
    elif monitor_context is not None:
        raise SystemExit("role must not receive monitor_context")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
