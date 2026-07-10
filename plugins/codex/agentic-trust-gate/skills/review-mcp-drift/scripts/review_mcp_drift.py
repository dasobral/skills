#!/usr/bin/env python3
"""Compare the full union of sanitized MCP capabilities under explicit policy."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:
    Draft202012Validator = None


EVIDENCE_STATES = {"pass", "fail", "unknown", "not-applicable", "evidence-gap"}
DECISIONS = {"allow", "deny", "review-required"}
CHECK_NAMES = {
    "destructive-capability-addition",
    "hidden-instructions",
    "remote-mutability",
    "scope-expansion",
    "shadowed-names",
    "token-passthrough",
}
HIDDEN_INSTRUCTION = re.compile(
    r"(?:<!--|conceal|ignore\s+(?:all\s+)?(?:prior|policy)|do\s+not\s+reveal)",
    re.IGNORECASE,
)
DESTRUCTIVE = re.compile(
    r"\b(?:admin|command|create|delete|destroy|execute|modify|mutate|remove|shell|upload|write)\b",
    re.IGNORECASE,
)
SCHEMA_PATH = (
    Path(__file__).parents[1]
    / "references"
    / "schemas"
    / "capability-delta.schema.json"
)
SNAPSHOT_SCHEMA_PATH = SCHEMA_PATH.with_name("mcp-snapshot.schema.json")
SETUP_GUIDANCE = "Install the pinned validator: python -m pip install jsonschema==4.26.0"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def _hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _draft_errors(value: object, schema_path: Path) -> list[str]:
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


def _schema_errors(value: object) -> list[str]:
    return _draft_errors(value, SCHEMA_PATH)


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


def _canonical_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _normalized_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _pointer(parts: tuple[object, ...]) -> str:
    return "/" + "/".join(
        str(part).replace("~", "~0").replace("/", "~1") for part in parts
    )


def _instruction_surfaces(snapshot: dict[str, Any]) -> list[tuple[str, str, object]]:
    server = _server(snapshot)
    surfaces: list[tuple[str, str, object]] = []
    if "instructions" in server:
        surfaces.append(("/server/instructions", "server-instructions", server["instructions"]))
    for index, tool in enumerate(server.get("tools", [])):
        if not isinstance(tool, dict):
            continue
        if "description" in tool:
            surfaces.append(
                (f"/server/tools/{index}/description", "tool-description", tool["description"])
            )

        def scan_schema(value: object, parts: tuple[object, ...]) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    child_parts = (*parts, key)
                    if key in {"description", "title", "$comment", "default", "examples"}:
                        surfaces.append(
                            (_pointer(child_parts), "schema-annotation", child)
                        )
                    scan_schema(child, child_parts)
            elif isinstance(value, list):
                for child_index, child in enumerate(value):
                    scan_schema(child, (*parts, child_index))

        scan_schema(
            tool.get("inputSchema", {}),
            ("server", "tools", index, "inputSchema"),
        )

    def scan_remote(value: object, parts: tuple[object, ...]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                scan_remote(child, (*parts, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan_remote(child, (*parts, index))
        else:
            surfaces.append((_pointer(parts), "remote-descriptor", value))

    if "remote_descriptor" in server:
        scan_remote(server["remote_descriptor"], ("server", "remote_descriptor"))
    return surfaces


def _instruction_findings(snapshot: dict[str, Any]) -> list[dict[str, object]]:
    findings = []
    for location, source_class, value in _instruction_surfaces(snapshot):
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if HIDDEN_INSTRUCTION.search(serialized):
            findings.append(
                {
                    "location": location,
                    "source_class": source_class,
                    "content_hash": _hash(value),
                    "evidence_state": "fail",
                    "decision": "deny",
                    "policy_action": "block",
                }
            )
    return sorted(findings, key=lambda finding: str(finding["location"]))


def _remote_leaves(snapshot: dict[str, Any]) -> dict[str, object]:
    server = _server(snapshot)
    leaves: dict[str, object] = {}

    def visit(value: object, parts: tuple[object, ...]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, (*parts, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, (*parts, index))
        else:
            leaves[_pointer(parts)] = value

    if "remote_descriptor" in server:
        visit(server["remote_descriptor"], ("server", "remote_descriptor"))
    return leaves


def _remote_descriptor_changes(
    before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, object]]:
    old = _remote_leaves(before)
    new = _remote_leaves(after)
    changes = []
    for location in sorted(set(old) | set(new)):
        if _canonical_bytes(old.get(location)) == _canonical_bytes(new.get(location)):
            continue
        blocked = bool(
            HIDDEN_INSTRUCTION.search(
                json.dumps(new.get(location), ensure_ascii=False, sort_keys=True)
            )
        )
        changes.append(
            {
                "location": location,
                "before_hash": _hash(old.get(location)),
                "after_hash": _hash(new.get(location)),
                "evidence_state": "fail" if blocked else "pass",
                "decision": "deny" if blocked else "review-required",
                "policy_action": "block" if blocked else "review",
            }
        )
    return changes


def _server(snapshot: dict[str, Any]) -> dict[str, Any]:
    server = snapshot.get("server")
    if not isinstance(server, dict):
        raise ValueError("snapshot.server must be an object")
    return server


def _tool_map(server: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    tools = server.get("tools", [])
    if not isinstance(tools, list):
        raise ValueError("server.tools must be a list")
    for tool in tools:
        if not isinstance(tool, dict) or not _canonical_name(tool.get("name")):
            raise ValueError("each MCP tool must have a canonicalizable name")
        result.setdefault(_canonical_name(tool["name"]), []).append(tool)
    return result


def _destructive(tool: dict[str, Any]) -> bool:
    material = " ".join(
        (
            str(tool.get("name", "")),
            str(tool.get("description", "")),
            json.dumps(tool.get("inputSchema", {}), sort_keys=True),
        )
    )
    return bool(DESTRUCTIVE.search(material))


def _change(
    *,
    field: str,
    change_type: str,
    before: object,
    after: object,
    decision: str,
    tool_name: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "field": field,
        "tool_name": tool_name,
        "change_type": change_type,
        "before_hash": _hash(before),
        "after_hash": _hash(after),
        "evidence_state": "pass",
        "decision": decision,
    }
    return result


def _check(
    name: str,
    failed: bool,
    evidence: list[str],
    *,
    decision_on_fail: str = "deny",
) -> dict[str, object]:
    result: dict[str, object] = {
        "check": name,
        "evidence_state": "fail" if failed else "pass",
        "decision": decision_on_fail if failed else "allow",
        "evidence": evidence,
    }
    return result


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, object]:
    for label, snapshot in (("before", before), ("after", after)):
        errors = _draft_errors(snapshot, SNAPSHOT_SCHEMA_PATH)
        if errors:
            raise ValueError(f"{label} snapshot {errors[0]}")
    old = _server(before)
    new = _server(after)
    old_tools = _tool_map(old)
    new_tools = _tool_map(new)
    changes: list[dict[str, object]] = []
    destructive_additions: list[str] = []

    for name in sorted(set(old_tools) | set(new_tools)):
        old_group = old_tools.get(name, [])
        new_group = new_tools.get(name, [])
        if not old_group:
            destructive = any(_destructive(tool) for tool in new_group)
            if destructive:
                destructive_additions.append(name)
            changes.append(
                _change(
                    field="tool",
                    tool_name=name,
                    change_type="added",
                    before=None,
                    after=new_group,
                    decision="deny" if destructive else "review-required",
                )
            )
            continue
        if not new_group:
            changes.append(
                _change(
                    field="tool",
                    tool_name=name,
                    change_type="removed",
                    before=old_group,
                    after=None,
                    decision="review-required",
                )
            )
            continue
        old_tool = old_group[0]
        new_tool = new_group[0]
        for field, left, right in (
            ("tool-schema", old_tool.get("inputSchema", {}), new_tool.get("inputSchema", {})),
            (
                "description",
                _normalized_text(old_tool.get("description")),
                _normalized_text(new_tool.get("description")),
            ),
        ):
            if _canonical_bytes(left) != _canonical_bytes(right):
                changes.append(
                    _change(
                        field=field,
                        tool_name=name,
                        change_type="modified",
                        before=left,
                        after=right,
                        decision=(
                            "deny"
                            if not _destructive(old_tool) and _destructive(new_tool)
                            else "review-required"
                        ),
                    )
                )
        if not _destructive(old_tool) and _destructive(new_tool):
            destructive_additions.append(name)
            changes.append(
                _change(
                    field="destructive-capability",
                    tool_name=name,
                    change_type="modified",
                    before=False,
                    after=True,
                    decision="deny",
                )
            )

    old_scopes = set(old.get("scopes", []))
    new_scopes = set(new.get("scopes", []))
    expanded = sorted(new_scopes - old_scopes)
    removed_scopes = sorted(old_scopes - new_scopes)
    if expanded or removed_scopes:
        changes.append(
            _change(
                field="scopes",
                change_type="modified",
                before=sorted(old_scopes),
                after=sorted(new_scopes),
                decision="deny" if expanded else "review-required",
            )
        )
    old_auth = _normalized_text(old.get("auth_endpoint"))
    new_auth = _normalized_text(new.get("auth_endpoint"))
    if old_auth != new_auth:
        changes.append(
            _change(
                field="auth-endpoint",
                change_type="modified",
                before=old_auth,
                after=new_auth,
                decision="deny",
            )
        )
    if _canonical_bytes(old.get("package", {})) != _canonical_bytes(
        new.get("package", {})
    ):
        changes.append(
            _change(
                field="package-identity",
                change_type="modified",
                before=old.get("package", {}),
                after=new.get("package", {}),
                decision="review-required",
            )
        )

    collisions = sorted(
        name for name, tools in new_tools.items() if len(tools) > 1
    )
    instruction_findings = _instruction_findings(after)
    remote_descriptor_changes = _remote_descriptor_changes(before, after)
    hidden = bool(instruction_findings)
    passthrough = new.get("token_passthrough")
    package = new.get("package", {})
    package = package if isinstance(package, dict) else {}
    version = str(package.get("version", ""))
    remote = str(package.get("source", ""))
    mutable = (
        version in {"", "latest", "*"}
        or bool(re.search(r"^[~^<>]", version))
        or (
            remote.startswith(("http://", "https://"))
            and not str(package.get("integrity", "")).startswith("sha256:")
        )
    )
    checks = [
        _check("shadowed-names", bool(collisions), collisions),
        _check("scope-expansion", bool(expanded), expanded),
        _check(
            "hidden-instructions",
            hidden,
            ["hidden instruction marker detected"] if hidden else [],
        ),
        {
            "check": "token-passthrough",
            "evidence_state": (
                "fail"
                if passthrough is True
                else "pass"
                if passthrough is False
                else "evidence-gap"
            ),
            "decision": "deny" if passthrough is True else (
                "allow" if passthrough is False else "review-required"
            ),
            "evidence": (
                ["token passthrough enabled"]
                if passthrough is True
                else ["token passthrough declaration missing"]
                if passthrough is None
                else []
            ),
        },
        _check(
            "remote-mutability",
            mutable,
            ["package source or version is mutable"] if mutable else [],
        ),
        _check(
            "destructive-capability-addition",
            bool(destructive_additions),
            sorted(set(destructive_additions)),
        ),
    ]
    decisions = {
        str(item["decision"])
        for item in [
            *changes,
            *checks,
            *instruction_findings,
            *remote_descriptor_changes,
        ]
    }
    overall_decision = (
        "deny"
        if "deny" in decisions
        else "review-required"
        if "review-required" in decisions
        else "allow"
    )
    states = {str(check["evidence_state"]) for check in checks}
    evidence_state = (
        "fail"
        if "fail" in states
        else "evidence-gap"
        if "evidence-gap" in states
        else "unknown"
        if "unknown" in states
        else "pass"
    )
    return {
        "schema_version": "2.0",
        "before_hash": _hash(before),
        "after_hash": _hash(after),
        "changes": sorted(
            changes,
            key=lambda item: (
                str(item.get("tool_name") or ""),
                str(item["field"]),
                str(item["change_type"]),
            ),
        ),
        "instruction_findings": instruction_findings,
        "remote_descriptor_changes": remote_descriptor_changes,
        "security_checks": checks,
        "evidence_state": evidence_state,
        "decision": overall_decision,
    }
    errors = validate(result)
    if errors:
        raise ValueError(f"generated capability delta {errors[0]}")
    return result


def validate(value: object) -> list[str]:
    schema_errors = _schema_errors(value)
    if schema_errors:
        return schema_errors
    if not isinstance(value, dict):
        return ["artifact must be an object"]
    errors: list[str] = []
    if value.get("evidence_state") not in EVIDENCE_STATES:
        errors.append("evidence_state is invalid")
    if value.get("decision") not in DECISIONS:
        errors.append("decision is invalid")
    checks = value.get("security_checks")
    if not isinstance(checks, list):
        errors.append("security_checks must be a list")
    else:
        names = {
            check.get("check") for check in checks if isinstance(check, dict)
        }
        if names != CHECK_NAMES:
            errors.append("security_checks must contain all required checks")
        for index, check in enumerate(checks):
            if (
                not isinstance(check, dict)
                or check.get("evidence_state") not in EVIDENCE_STATES
                or check.get("decision") not in DECISIONS
            ):
                errors.append(f"security_checks[{index}] is invalid")
    for field in ("before_hash", "after_hash"):
        if not str(value.get(field, "")).startswith("sha256:"):
            errors.append(f"{field} is invalid")
    if not isinstance(value.get("changes"), list):
        errors.append("changes must be a list")
    return errors


def _read(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def main() -> None:
    if Draft202012Validator is None:
        _dependency_gap()
    if len(sys.argv) == 3 and sys.argv[1] == "--validate":
        errors = validate(_read(sys.argv[2]))
        print(json.dumps({"valid": not errors, "errors": errors}, sort_keys=True))
        raise SystemExit(0 if not errors else 1)
    if len(sys.argv) != 3:
        raise SystemExit("usage: review_mcp_drift.py BEFORE.json AFTER.json")
    try:
        result = compare(_read(sys.argv[1]), _read(sys.argv[2]))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
