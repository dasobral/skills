#!/usr/bin/env python3
"""Build a deterministic attack scenario without embedding fixture contents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:
    Draft202012Validator = None


STATUSES = {"pass", "fail", "unknown", "not-applicable", "evidence-gap"}
SCENARIO_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SCHEMA_PATH = (
    Path(__file__).parents[1] / "references" / "schemas" / "scenario.schema.json"
)
DEFINITION_SCHEMA_PATH = SCHEMA_PATH.with_name("scenario-definition.schema.json")
ROLE_DEFINITIONS = (
    Path(__file__).parents[2]
    / "run-agent-attack-replay"
    / "references"
    / "roles"
)
SETUP_GUIDANCE = "Install the pinned validator: python -m pip install jsonschema==4.26.0"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _schema_errors(value: object, schema_path: Path = SCHEMA_PATH) -> list[str]:
    if Draft202012Validator is None:
        return ["schema: jsonschema dependency unavailable"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    return [
        "schema: /"
        + "/".join(str(part) for part in error.absolute_path)
        + f" violates {error.validator}"
        for error in errors
    ]


def _dependency_gap() -> None:
    print(
        json.dumps(
            {
                "valid": False,
                "evidence_state": "evidence-gap",
                "errors": ["jsonschema dependency unavailable"],
                "setup_guidance": SETUP_GUIDANCE,
            },
            sort_keys=True,
        )
    )
    raise SystemExit(2)


def validate(value: object) -> list[str]:
    schema_errors = _schema_errors(value)
    if schema_errors:
        return schema_errors
    if not isinstance(value, dict):
        return ["artifact must be an object"]
    errors: list[str] = []
    required_strings = (
        "scenario_id",
        "trusted_goal",
        "untrusted_channel",
        "attack_payload_family",
    )
    for field in required_strings:
        if not isinstance(value.get(field), str) or not value[field]:
            errors.append(f"{field} must be a non-empty string")
    if isinstance(value.get("scenario_id"), str) and not SCENARIO_ID.fullmatch(
        value["scenario_id"]
    ):
        errors.append("scenario_id must be lowercase kebab-case")
    for field in ("prohibited_side_effects", "benign_success_criteria"):
        values = value.get(field)
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(item, str) or not item for item in values)
        ):
            errors.append(f"{field} must be a non-empty string list")
    role_inputs = value.get("role_inputs")
    if (
        not isinstance(role_inputs, dict)
        or set(role_inputs) != {"attacker", "victim", "judge"}
        or any(not isinstance(role_inputs[role], dict) for role in role_inputs)
    ):
        errors.append("role_inputs must separate attacker, victim, and judge objects")
    benign_assertions = value.get("benign_assertions")
    if not isinstance(benign_assertions, list) or not benign_assertions:
        errors.append("benign_assertions must be a non-empty list")
    elif {
        assertion.get("id")
        for assertion in benign_assertions
        if isinstance(assertion, dict)
    } != set(value.get("benign_success_criteria", [])):
        errors.append("benign_assertions must exactly cover benign_success_criteria")
    repetitions = value.get("repetitions")
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions < 1:
        errors.append("repetitions must be a positive integer")
    fixture_hashes = value.get("fixture_hashes")
    if not isinstance(fixture_hashes, list) or not fixture_hashes:
        errors.append("fixture_hashes must be a non-empty list")
    else:
        for index, item in enumerate(fixture_hashes):
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("path"), str)
                or not str(item.get("content_hash", "")).startswith("sha256:")
            ):
                errors.append(f"fixture_hashes[{index}] is invalid")
    role_hashes = value.get("role_definition_hashes")
    if (
        not isinstance(role_hashes, dict)
        or set(role_hashes) != {"attacker", "victim", "judge"}
        or any(not str(item).startswith("sha256:") for item in role_hashes.values())
    ):
        errors.append("role_definition_hashes must bind all packaged roles")
    if value.get("evidence_state") not in STATUSES:
        errors.append("evidence_state is invalid")
    return errors


def build(definition: dict[str, Any], base_dir: Path) -> dict[str, object]:
    schema_errors = _schema_errors(definition, DEFINITION_SCHEMA_PATH)
    if schema_errors:
        raise ValueError(f"scenario definition {schema_errors[0]}")
    fixtures = definition.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixtures must be a non-empty list")
    base_dir = base_dir.expanduser().resolve()
    hashes: list[dict[str, str]] = []
    for raw in fixtures:
        if not isinstance(raw, str):
            raise ValueError("fixture paths must be strings")
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe fixture path: {raw}")
        fixture = (base_dir / relative).resolve()
        if not fixture.is_relative_to(base_dir) or fixture.is_symlink():
            raise ValueError(f"fixture escapes base directory: {raw}")
        if not fixture.is_file():
            raise ValueError(f"fixture does not exist: {raw}")
        hashes.append({"path": relative.as_posix(), "content_hash": _hash_file(fixture)})
    output = {
        "schema_version": "1.0",
        "scenario_id": definition.get("scenario_id"),
        "trusted_goal": definition.get("trusted_goal"),
        "untrusted_channel": definition.get("untrusted_channel"),
        "attack_payload_family": definition.get("attack_payload_family"),
        "prohibited_side_effects": sorted(
            set(definition.get("prohibited_side_effects", []))
        ),
        "benign_success_criteria": sorted(
            set(definition.get("benign_success_criteria", []))
        ),
        "benign_assertions": definition.get("benign_assertions"),
        "role_inputs": definition.get("role_inputs"),
        "role_definition_hashes": {
            role: _hash_file(ROLE_DEFINITIONS / f"{role}.toml")
            for role in ("attacker", "victim", "judge")
        },
        "repetitions": definition.get("repetitions"),
        "fixture_hashes": sorted(hashes, key=lambda item: item["path"]),
        "evidence_state": "pass",
    }
    errors = validate(output)
    if errors:
        raise ValueError("; ".join(errors))
    return output


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def main() -> None:
    if Draft202012Validator is None:
        _dependency_gap()
    parser = argparse.ArgumentParser()
    parser.add_argument("definition", type=Path)
    parser.add_argument("--base-dir", type=Path)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        errors = validate(_read(args.definition))
        print(json.dumps({"valid": not errors, "errors": errors}, sort_keys=True))
        raise SystemExit(0 if not errors else 1)
    base_dir = args.base_dir or args.definition.parent
    try:
        result = build(_read(args.definition), base_dir)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
