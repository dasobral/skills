#!/usr/bin/env python3
"""Validate crypto evidence files touched by authentic Codex tool hooks."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from control_state import trust_root, verify_approval

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError:  # Optional hook dependency unavailable in the host Codex.
    Draft202012Validator = None
    SchemaError = ValidationError = ValueError


SCHEMAS = {
    "cbom.json": ("build-crypto-inventory", "cbom.schema.json"),
    "cbom-delta.json": ("review-crypto-delta", "cbom-delta.schema.json"),
    "pqc-queue.json": ("plan-pqc-migration", "pqc-queue.schema.json"),
    "interoperability-case.json": (
        "test-crypto-interoperability",
        "interoperability-case.schema.json",
    ),
}
POLICY_FILE = "crypto-policy.json"
PLUGIN_NAME = "crypto-change-radar"
TRUST_ENV = "CRYPTO_CHANGE_RADAR_TRUST_ROOT"
RUNTIME_GUIDANCE = (
    "evidence-state=evidence-gap: jsonschema==4.26.0 unavailable; "
    "run check-crypto-runtime"
)


def _candidate_paths(tool_name: str, tool_input: object) -> list[str]:
    if not isinstance(tool_input, dict):
        return []
    if tool_name in {"Write", "Edit"}:
        value = tool_input.get("file_path") or tool_input.get("path")
        return [value] if isinstance(value, str) else []
    command = tool_input.get("command")
    if not isinstance(command, str):
        return []
    if tool_name == "apply_patch":
        return re.findall(
            r"^\*\*\* (?:Add|Update|Delete) File: (.+)$",
            command,
            flags=re.MULTILINE,
        )
    if tool_name == "Bash":
        return re.findall(r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_./-]+\.json)", command)
    return []


def _schema_path(skill: str, schema: str) -> Path | None:
    script = Path(__file__).resolve()
    plugin_root = script.parents[2]
    candidates = [
        plugin_root / "skills" / skill / "references" / schema,
        script.parents[5] / "core" / "skills" / skill / "references" / schema,
    ]
    return next((path for path in candidates if path.is_file()), None)


def _affected(payload: dict[str, object]) -> list[tuple[str, Path, tuple[str, str]]]:
    cwd = Path(str(payload["cwd"])).expanduser().resolve()
    result = []
    for raw in _candidate_paths(
        str(payload.get("tool_name", "")), payload.get("tool_input")
    ):
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        contract = SCHEMAS.get(relative.name.lower())
        target = (cwd / relative).resolve()
        if contract and target.is_relative_to(cwd):
            result.append((relative.as_posix(), target, contract))
    return sorted(set(result), key=lambda item: item[0])


def _protected_attempts(payload: dict[str, object]) -> list[str]:
    return sorted(
        {
            Path(raw).as_posix()
            for raw in _candidate_paths(
                str(payload.get("tool_name", "")), payload.get("tool_input")
            )
            if Path(raw).name.lower() == POLICY_FILE
        }
    )


def _validate(target: Path, contract: tuple[str, str]) -> str:
    if not target.is_file():
        return "evidence-gap"
    if Draft202012Validator is None:
        return "evidence-gap"
    schema_path = _schema_path(*contract)
    if schema_path is None:
        return "evidence-gap"
    try:
        instance = json.loads(target.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        SchemaError,
        ValidationError,
    ):
        return "fail"
    return "pass"


def _state_dir(cwd: Path) -> Path | None:
    explicit = os.environ.get("CRYPTO_CHANGE_RADAR_STATE_DIR")
    plugin_data = os.environ.get("PLUGIN_DATA")
    raw = explicit or (str(Path(plugin_data) / PLUGIN_NAME) if plugin_data else None)
    if raw is None:
        return None
    try:
        state = Path(raw).expanduser().resolve(strict=True)
    except OSError:
        return None
    if not state.is_dir() or state.is_relative_to(cwd):
        return None
    return state


def _load_policy(cwd: Path) -> tuple[dict[str, object] | None, str]:
    state = _state_dir(cwd)
    if state is None:
        return None, "fail: authenticated external state is missing or unsafe"
    root, root_state = trust_root(state, PLUGIN_NAME, TRUST_ENV)
    if root is None:
        return None, "fail: evidence-gap: " + root_state
    policy, approval_state = verify_approval(
        state, PLUGIN_NAME, POLICY_FILE, root
    )
    if policy is None:
        return None, approval_state
    if not isinstance(policy, dict):
        return None, "fail: crypto policy must be an object"
    expected_keys = {"policy_version", "forbidden_primitives"}
    version = policy.get("policy_version")
    primitives = policy.get("forbidden_primitives")
    if (
        set(policy) != expected_keys
        or not isinstance(version, str)
        or not re.fullmatch(r"[a-z0-9_.-]+@\d{4}-\d{2}-\d{2}", version)
        or not isinstance(primitives, list)
        or not primitives
        or not all(isinstance(item, str) and item.strip() for item in primitives)
    ):
        return None, "fail: external crypto policy is not strict and version-pinned"
    schema_path = _schema_path("build-crypto-inventory", "crypto-policy.schema.json")
    if Draft202012Validator is not None:
        try:
            if schema_path is None:
                raise ValueError("schema unavailable")
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(policy)
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            SchemaError,
            ValidationError,
            ValueError,
        ):
            return None, "fail: external crypto policy fails its strict schema"
    return policy, "pass"


def _selected_forbidden(target: Path, policy: dict[str, object]) -> list[str]:
    try:
        artifact = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    selected = []
    if isinstance(artifact, dict):
        for asset in artifact.get("assets", []):
            if not isinstance(asset, dict):
                continue
            values = " ".join(
                str(asset.get(field, ""))
                for field in (
                    "algorithm",
                    "fallback",
                    "mode",
                    "protocol",
                    "provider_boundary",
                )
            )
            for primitive in policy["forbidden_primitives"]:
                if re.search(rf"(?<![A-Za-z0-9]){re.escape(primitive)}(?![A-Za-z0-9])", values, re.IGNORECASE):
                    selected.append(primitive)
    return sorted(set(selected), key=str.casefold)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return
        event = payload.get("hook_event_name")
        if event not in {"PreToolUse", "PostToolUse"}:
            return
        protected = _protected_attempts(payload)
        if protected:
            reason = (
                "Project crypto policy changes are forbidden; register policy "
                "through external control-plane state: " + ", ".join(protected)
            )
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": reason,
                        "hookSpecificOutput": {
                            "hookEventName": event,
                            "decision": "block",
                            "additionalContext": "evidence-state=fail: " + reason,
                        },
                    },
                    sort_keys=True,
                )
            )
            return
        affected = _affected(payload)
        if not affected:
            return
        policy, policy_state = _load_policy(
            Path(str(payload["cwd"])).expanduser().resolve()
        )
        if policy is None:
            reason = "Objective crypto policy failure: " + policy_state.removeprefix(
                "fail: "
            )
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": reason,
                        "hookSpecificOutput": {
                            "hookEventName": event,
                            "decision": "block",
                            "additionalContext": "evidence-state=fail: " + reason,
                        },
                    },
                    sort_keys=True,
                )
            )
            return
        if event == "PreToolUse":
            context = "affected crypto evidence files: " + ", ".join(
                relative for relative, _, _ in affected
            )
        else:
            if Draft202012Validator is None:
                context = "; ".join(
                    f"{relative}: {RUNTIME_GUIDANCE}"
                    for relative, _, _ in affected
                )
            else:
                results = []
                failures = []
                for relative, target, contract in affected:
                    state = _validate(target, contract)
                    reason = None
                    if state == "pass" and policy is not None:
                        forbidden = _selected_forbidden(target, policy)
                        if forbidden:
                            state = "fail"
                            reason = (
                                "version-pinned policy forbids selected primitives: "
                                + ", ".join(forbidden)
                            )
                    summary = f"{relative}: evidence-state={state}"
                    if reason:
                        summary += f" ({reason})"
                    results.append(summary)
                    if state == "fail":
                        failures.append(summary)
                context = "; ".join(results)
            output = {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": context,
                }
            }
            if Draft202012Validator is not None and failures:
                reason = "Objective crypto policy failure: " + " | ".join(failures)
                output.update({"decision": "block", "reason": reason})
                output["hookSpecificOutput"]["decision"] = "block"
            print(json.dumps(output, sort_keys=True))
            return
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": context,
                    }
                },
                sort_keys=True,
            )
        )
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return


if __name__ == "__main__":
    main()
