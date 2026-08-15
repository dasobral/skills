#!/usr/bin/env python3
"""Create parameter-bound repository trust decisions and a hash-linked ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import trust_state

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:
    Draft202012Validator = None


EVIDENCE_STATES = {"pass", "fail", "unknown", "not-applicable", "evidence-gap"}
DECISIONS = {"allow", "deny", "review-required"}
CAPABILITIES = {
    "agent-instruction": "influence-agent-behavior",
    "hook": "execute-on-agent-event",
    "skill": "influence-agent-workflow",
    "mcp-config": "connect-external-tools",
    "lifecycle-script": "execute-lifecycle-command",
    "editor-task": "execute-editor-command",
    "devcontainer": "configure-development-environment",
    "symlink": "redirect-filesystem-access",
    "executable": "execute-repository-program",
}
SCHEMA_PATH = (
    Path(__file__).parents[1]
    / "references"
    / "schemas"
    / "trust-inventory.schema.json"
)
LEDGER_SCHEMA_PATH = SCHEMA_PATH.with_name("trust-ledger-entry.schema.json")
ANCHOR_SCHEMA_PATH = SCHEMA_PATH.with_name("trust-anchor.schema.json")
SETUP_GUIDANCE = "Install the pinned validator: python -m pip install jsonschema==4.26.0"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def _hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _hash_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


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


def _git(root: Path, *arguments: str, text: bool = True) -> str | bytes | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            capture_output=True,
            text=text,
            timeout=3,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return None


def _revision(root: Path) -> str:
    value = _git(root, "rev-parse", "HEAD")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unversioned"


def _repository_identity(root: Path) -> tuple[str, str, str]:
    marker = root / ".agent-trust-repository-id"
    if marker.is_file() and not marker.is_symlink():
        try:
            value = marker.read_bytes()
            if value and len(value) <= 512:
                return _hash_bytes(value), "repository-id-file", "pass"
        except OSError:
            pass
    remote = _git(root, "config", "--get", "remote.origin.url")
    if isinstance(remote, str) and remote.strip():
        normalized = re.sub(
            r"(?i)(https?://)[^/@]+@", r"\1", remote.strip().split("?", 1)[0]
        )
        material = {"kind": "git-origin", "value": normalized}
        return _hash(material), "git-origin", "pass"
    else:
        material = {"kind": "local-name", "value": root.name}
        return _hash(material), "local-name-fallback", "unknown"


def _source_classes(path: Path, relative: Path) -> list[str]:
    posix = relative.as_posix().lower()
    name = relative.name.lower()
    classes: set[str] = set()
    if name in {"agents.md", "claude.md", "gemini.md"} or ".cursor/rules/" in posix:
        classes.add("agent-instruction")
    if "hook" in name or "/hooks/" in f"/{posix}":
        classes.add("hook")
    if name == "skill.md":
        classes.add("skill")
    if name in {".mcp.json", "mcp.json"} or "mcpservers" in name:
        classes.add("mcp-config")
    if name in {
        "package.json",
        "makefile",
        "justfile",
        "taskfile.yml",
        "taskfile.yaml",
    } or "/scripts/" in f"/{posix}":
        classes.add("lifecycle-script")
    if posix in {".vscode/tasks.json", ".idea/runconfigurations"} or (
        "/.idea/runconfigurations/" in f"/{posix}"
    ):
        classes.add("editor-task")
    if posix.startswith(".devcontainer/") or name == "devcontainer.json":
        classes.add("devcontainer")
    if path.is_symlink():
        classes.add("symlink")
    try:
        if path.is_file() and path.stat().st_mode & (
            stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        ):
            classes.add("executable")
    except OSError:
        pass
    return sorted(classes)


def _item(path: Path, relative: Path, source_class: str) -> dict[str, str]:
    try:
        content_hash = (
            _hash_bytes(os.readlink(path).encode("utf-8", "surrogateescape"))
            if path.is_symlink()
            else _hash_file(path)
        )
        evidence_state = "pass"
    except OSError:
        content_hash = _hash({"unreadable": relative.as_posix()})
        evidence_state = "evidence-gap"
    return {
        "source_class": source_class,
        "path": relative.as_posix(),
        "requested_capability": CAPABILITIES[source_class],
        "content_hash": content_hash,
        "evidence_state": evidence_state,
    }


def _inventory_items(root: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        relative = path.relative_to(root)
        if ".git" in relative.parts or (path.is_dir() and not path.is_symlink()):
            continue
        for source_class in _source_classes(path, relative):
            items.append(_item(path, relative, source_class))
    return items


def _dirty_state_hash(root: Path, revision: str) -> str:
    records: list[dict[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        relative = path.relative_to(root)
        if ".git" in relative.parts or (path.is_dir() and not path.is_symlink()):
            continue
        try:
            content_hash = (
                _hash_bytes(os.readlink(path).encode("utf-8", "surrogateescape"))
                if path.is_symlink()
                else _hash_file(path)
            )
        except OSError:
            content_hash = _hash({"unreadable": relative.as_posix()})
        records.append({"path": relative.as_posix(), "content_hash": content_hash})
    return _hash({"revision": revision, "working_tree": records})


def _item_map(items: object) -> dict[tuple[str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        key = (
            str(item.get("source_class", "")),
            str(item.get("path", "")),
            str(item.get("requested_capability", "")),
        )
        result[key] = item
    return result


def _capability_delta(
    prior_items: object, current_items: list[dict[str, str]]
) -> dict[str, list[dict[str, str]]]:
    old = _item_map(prior_items)
    new = _item_map(current_items)
    added = [
        {
            "source_class": key[0],
            "path": key[1],
            "requested_capability": key[2],
            "content_hash": str(new[key].get("content_hash", "")),
        }
        for key in sorted(set(new) - set(old))
    ]
    removed = [
        {
            "source_class": key[0],
            "path": key[1],
            "requested_capability": key[2],
            "content_hash": str(old[key].get("content_hash", "")),
        }
        for key in sorted(set(old) - set(new))
    ]
    changed = [
        {
            "source_class": key[0],
            "path": key[1],
            "requested_capability": key[2],
            "before_hash": str(old[key].get("content_hash", "")),
            "after_hash": str(new[key].get("content_hash", "")),
        }
        for key in sorted(set(old) & set(new))
        if old[key].get("content_hash") != new[key].get("content_hash")
    ]
    return {"added": added, "removed": removed, "changed": changed}


def _parameters(values: list[str]) -> list[dict[str, str]]:
    parameters: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in values:
        key, separator, raw = value.partition("=")
        if not separator or not key or key in seen:
            raise ValueError("parameters must be unique KEY=VALUE pairs")
        seen.add(key)
        parameters.append({"name": key, "value_hash": _hash(raw)})
    return sorted(parameters, key=lambda item: item["name"])


def _binding_material(value: dict[str, Any]) -> dict[str, object]:
    repository = value["repository"]
    return {
        "repository_identity": repository["identity"],
        "revision": repository["revision"],
        "dirty_state_hash": repository["dirty_state_hash"],
        "prior_approved_snapshot_hash": value["prior_approved_snapshot_hash"],
        "capability_delta_hash": _hash(value["capability_delta"]),
        "requested_capabilities": value["request"]["requested_capabilities"],
        "parameters": value["request"]["parameters"],
    }


def _binding_is_valid(value: dict[str, Any]) -> bool:
    return value["decision"]["binding_hash"] == _hash(_binding_material(value))


def _applicability_hash(value: dict[str, Any]) -> str:
    return _hash(
        {
            "repository_identity": value["repository"]["identity"],
            "requested_capabilities": value["request"][
                "requested_capabilities"
            ],
            "parameters": value["request"]["parameters"],
        }
    )


def assess(
    root: Path,
    *,
    approved_snapshot: Path | None,
    requested_capabilities: list[str],
    parameters: list[str],
    policy_id: str | None,
    policy_version: str | None,
    approver_id: str | None,
    explicit_decision: str | None,
    state_dir: Path | None,
    approved_anchor: str | None,
    external_record_available: bool,
) -> dict[str, object]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("repository must be an existing directory")
    items = _inventory_items(root)
    revision = _revision(root)
    identity, identity_source, identity_evidence_state = _repository_identity(root)
    repository = {
        "identity": identity,
        "identity_source": identity_source,
        "identity_evidence_state": identity_evidence_state,
        "name": root.name,
        "revision": revision,
        "dirty_state_hash": _dirty_state_hash(root, revision),
    }
    prior: dict[str, Any] | None = None
    prior_hash: str | None = None
    prior_valid = True
    prior_failure: str | None = None
    if approved_snapshot is not None:
        value = json.loads(approved_snapshot.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("approved snapshot must contain an object")
        prior = value
        schema_errors = _schema_errors(prior)
        if schema_errors:
            raise ValueError(f"approved snapshot {schema_errors[0]}")
        prior_hash = _hash(prior)
        prior_valid = (
            prior.get("repository", {}).get("identity") == repository["identity"]
            and prior.get("decision", {}).get("value") == "allow"
        )
        if prior_valid and not _binding_is_valid(prior):
            prior_valid = False
            prior_failure = "invalid-approved-snapshot-binding"
        elif prior_valid and (state_dir is None or approved_anchor is None):
            prior_valid = False
            prior_failure = "invalid-authenticated-approved-snapshot"
        elif prior_valid:
            authenticated, _ = trust_state.authenticate_snapshot(
                state_dir,
                anchor_name=approved_anchor,
                artifact_hash=prior_hash,
                binding_hash=prior["decision"]["binding_hash"],
                applicability_hash=_applicability_hash(prior),
                entry_schema_check=lambda artifact: _schema_errors(
                    artifact, LEDGER_SCHEMA_PATH
                ),
                anchor_schema_check=lambda artifact: _schema_errors(
                    artifact, ANCHOR_SCHEMA_PATH
                ),
            )
            if not authenticated:
                prior_valid = False
                prior_failure = "invalid-authenticated-approved-snapshot"
    delta = _capability_delta(prior.get("items") if prior else [], items)
    parameter_evidence = _parameters(parameters)
    binding_material = {
        "repository_identity": repository["identity"],
        "revision": repository["revision"],
        "dirty_state_hash": repository["dirty_state_hash"],
        "prior_approved_snapshot_hash": prior_hash,
        "capability_delta_hash": _hash(delta),
        "requested_capabilities": sorted(set(requested_capabilities)),
        "parameters": parameter_evidence,
    }
    if prior is not None and not prior_valid:
        decision_value = "deny"
        provenance = prior_failure or "invalid-authenticated-approved-snapshot"
    elif explicit_decision == "allow" and not external_record_available:
        decision_value = "deny"
        provenance = "missing-authenticated-external-state"
    elif explicit_decision is not None:
        if not all((policy_id, policy_version, approver_id)):
            raise ValueError(
                "explicit decision requires policy id/version and approver id"
            )
        decision_value = explicit_decision
        provenance = "explicit-approval-record"
    else:
        decision_value = "deny" if not prior_valid else "review-required"
        provenance = "unapproved-request"
    states = {
        identity_evidence_state,
        *(item["evidence_state"] for item in items),
    }
    evidence_state = (
        "evidence-gap"
        if "evidence-gap" in states
        else "fail"
        if not prior_valid
        else "unknown"
        if "unknown" in states
        else "pass"
    )
    result: dict[str, object] = {
        "schema_version": "2.0",
        "repository": repository,
        "items": items,
        "prior_approved_snapshot_hash": prior_hash,
        "capability_delta": delta,
        "request": {
            "requested_capabilities": sorted(set(requested_capabilities)),
            "parameters": parameter_evidence,
        },
        "evidence_state": evidence_state,
        "decision": {
            "value": decision_value,
            "binding_hash": _hash(binding_material),
            "policy": {"id": policy_id, "version": policy_version},
            "approver": {"id": approver_id},
            "provenance": provenance,
        },
    }
    artifact_errors = validate(result)
    if artifact_errors:
        raise ValueError(f"generated trust inventory {artifact_errors[0]}")
    return result


def validate(value: object) -> list[str]:
    schema_errors = _schema_errors(value)
    if schema_errors:
        return schema_errors
    if not isinstance(value, dict):
        return ["artifact must be an object"]
    errors: list[str] = []
    repository = value.get("repository")
    if not isinstance(repository, dict):
        errors.append("repository must be an object")
    else:
        for field in (
            "identity",
            "identity_source",
            "identity_evidence_state",
            "name",
            "revision",
            "dirty_state_hash",
        ):
            if not isinstance(repository.get(field), str) or not repository[field]:
                errors.append(f"repository.{field} must be a non-empty string")
    if value.get("evidence_state") not in EVIDENCE_STATES:
        errors.append("evidence_state is invalid")
    decision = value.get("decision")
    if not isinstance(decision, dict) or decision.get("value") not in DECISIONS:
        errors.append("decision is invalid")
    elif decision.get("binding_hash") != _hash(_binding_material(value)):
        errors.append("decision binding hash mismatch")
    items = value.get("items")
    if not isinstance(items, list):
        errors.append("items must be a list")
    elif any(
        not isinstance(item, dict)
        or item.get("evidence_state") not in EVIDENCE_STATES
        for item in items
    ):
        errors.append("item evidence_state is invalid")
    delta = value.get("capability_delta")
    if not isinstance(delta, dict) or set(delta) != {"added", "removed", "changed"}:
        errors.append("capability_delta is invalid")
    return errors


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def main() -> None:
    if Draft202012Validator is None:
        _dependency_gap()
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-ledger":
        result = trust_state.verify_ledger(
            Path(sys.argv[2]).expanduser().resolve(),
            lambda artifact: _schema_errors(artifact, LEDGER_SCHEMA_PATH),
        )
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(0 if result["valid"] else 1)
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("--approved-snapshot", type=Path)
    parser.add_argument("--approved-anchor")
    parser.add_argument("--requested-capability", action="append", default=[])
    parser.add_argument("--parameter", action="append", default=[])
    parser.add_argument("--policy-id")
    parser.add_argument("--policy-version")
    parser.add_argument("--approver-id")
    parser.add_argument("--decision", choices=sorted(DECISIONS))
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--anchor-out")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        value = _read(args.repository)
        errors = validate(value)
        if not errors and value["decision"]["value"] == "allow":
            if args.approved_anchor is None:
                errors.append(
                    "allow validation requires authenticated external anchor"
                )
            else:
                try:
                    state_dir = trust_state.resolve_state_dir(args.state_dir)
                    authenticated, reason = trust_state.authenticate_snapshot(
                        state_dir,
                        anchor_name=args.approved_anchor,
                        artifact_hash=_hash(value),
                        binding_hash=value["decision"]["binding_hash"],
                        applicability_hash=_applicability_hash(value),
                        entry_schema_check=lambda artifact: _schema_errors(
                            artifact, LEDGER_SCHEMA_PATH
                        ),
                        anchor_schema_check=lambda artifact: _schema_errors(
                            artifact, ANCHOR_SCHEMA_PATH
                        ),
                    )
                    if not authenticated:
                        errors.append(
                            reason or "authenticated allow validation failed"
                        )
                except ValueError as exc:
                    errors.append(str(exc))
        print(json.dumps({"valid": not errors, "errors": errors}, sort_keys=True))
        raise SystemExit(0 if not errors else 1)
    try:
        state_dir = (
            trust_state.resolve_state_dir(args.state_dir)
            if args.state_dir is not None or os.environ.get("PLUGIN_DATA")
            else None
        )
        result = assess(
            args.repository,
            approved_snapshot=args.approved_snapshot,
            requested_capabilities=args.requested_capability,
            parameters=args.parameter,
            policy_id=args.policy_id,
            policy_version=args.policy_version,
            approver_id=args.approver_id,
            explicit_decision=args.decision,
            state_dir=state_dir,
            approved_anchor=args.approved_anchor,
            external_record_available=(
                state_dir is not None and args.anchor_out is not None
            ),
        )
        if args.anchor_out is not None:
            if state_dir is None:
                raise ValueError("trust anchor requires authenticated external state")
            if args.decision is None:
                raise ValueError("trust ledger append requires an explicit decision")
            trust_state.append_record(
                state_dir,
                artifact_hash=_hash(result),
                binding_hash=result["decision"]["binding_hash"],
                applicability_hash=_applicability_hash(result),
                prior_snapshot_hash=result["prior_approved_snapshot_hash"],
                decision=result["decision"]["value"],
                policy=result["decision"]["policy"],
                approver=result["decision"]["approver"],
                anchor_name=args.anchor_out,
                entry_schema_check=lambda artifact: _schema_errors(
                    artifact, LEDGER_SCHEMA_PATH
                ),
                anchor_schema_check=lambda artifact: _schema_errors(
                    artifact, ANCHOR_SCHEMA_PATH
                ),
            )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
