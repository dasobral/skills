#!/usr/bin/env python3
"""Validate claim evidence without allowing agent-only acceptance."""

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
    Draft202012Validator = None  # type: ignore[assignment,misc]


SCHEMA_PATH = (
    Path(__file__).parents[1] / "references" / "claim-evidence-graph.schema.json"
)
RUN_SCHEMA_PATH = (
    Path(__file__).parents[2]
    / "capture-scientific-run"
    / "references"
    / "run-record.schema.json"
)
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _canonical_run_id(record: dict[str, Any]) -> str:
    content = {key: value for key, value in record.items() if key != "run_id"}
    canonical = json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"run-sha256:{hashlib.sha256(canonical).hexdigest()}"


def _resolve_contained(
    raw: Any, evidence_root: Path, path: str
) -> tuple[Path | None, list[str]]:
    if not isinstance(raw, str):
        return None, []
    normalized = raw.replace("\\", "/")
    parts = Path(normalized).parts
    if (
        Path(normalized).is_absolute()
        or re.match(r"^[A-Za-z]:/", normalized)
        or ".." in parts
    ):
        return None, [f"{path}: path escapes evidence root"]
    try:
        target = (evidence_root / normalized).resolve()
    except OSError as exc:
        return None, [f"{path}: cannot resolve referenced artifact: {exc}"]
    if not target.is_relative_to(evidence_root):
        return None, [f"{path}: path escapes evidence root"]
    return target, []


def _artifact_errors(
    edge: dict[str, Any], index: int, evidence_root: Path
) -> list[str]:
    path = f"$.edges[{index}].artifact_path"
    raw = edge.get("artifact_path")
    target, errors = _resolve_contained(raw, evidence_root, path)
    if target is None:
        return errors
    if not target.is_file():
        return [f"{path}: referenced artifact is missing"]
    expected = edge.get("artifact_hash")
    if isinstance(expected, str):
        try:
            actual = _sha256(target)
        except OSError as exc:
            return [f"{path}: cannot hash referenced artifact: {exc}"]
        if actual != expected:
            return [f"{path}: artifact SHA-256 mismatch"]
    return []


def _run_records(
    graph: dict[str, Any], evidence_root: Path, run_schema: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    references = graph.get("runs")
    if not isinstance(references, list):
        return records, errors
    validator = Draft202012Validator(run_schema)
    for index, reference in enumerate(references):
        base = f"$.runs[{index}]"
        if not isinstance(reference, dict):
            continue
        run_id = reference.get("run_id")
        target, path_errors = _resolve_contained(
            reference.get("run_record_path"),
            evidence_root,
            f"{base}.run_record_path",
        )
        errors.extend(path_errors)
        if target is None:
            continue
        if not target.is_file():
            errors.append(f"{base}.run_record_path: referenced run record is missing")
            continue
        try:
            actual_hash = _sha256(target)
            record = json.loads(
                target.read_text(encoding="utf-8"),
                parse_constant=_reject_constant,
            )
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{base}.run_record_path: unreadable run record: {exc}")
            continue
        if actual_hash != reference.get("run_record_hash"):
            errors.append(f"{base}.run_record_hash: run record SHA-256 mismatch")
        for error in validator.iter_errors(record):
            errors.append(
                f"{base}.run_record{_format_path(error.absolute_path)[1:]}: "
                f"{error.message}"
            )
        if not isinstance(record, dict):
            continue
        record_run_id = record.get("run_id")
        try:
            canonical_run_id = _canonical_run_id(record)
        except (TypeError, ValueError) as exc:
            errors.append(f"{base}.run_record: cannot compute run_id: {exc}")
            continue
        if record_run_id != canonical_run_id:
            errors.append(f"{base}.run_record.run_id: run_id content hash mismatch")
        if run_id != record_run_id:
            errors.append(f"{base}.run_id: does not match referenced run record")
        if isinstance(run_id, str):
            if run_id in records:
                errors.append(f"{base}.run_id: duplicate run reference")
            records[run_id] = record
    return records, errors


def validate(graph: Any, evidence_root: Path) -> list[str]:
    if Draft202012Validator is None:
        return [DEPENDENCY_GUIDANCE]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    run_schema = json.loads(RUN_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(run_schema)
    errors = [
        f"{_format_path(error.absolute_path)}: {error.message}"
        for error in Draft202012Validator(schema).iter_errors(graph)
    ]
    if not isinstance(graph, dict):
        return sorted(set(errors))
    edges = graph.get("edges", [])
    if not isinstance(edges, list):
        return sorted(set(errors))
    run_records, run_errors = _run_records(graph, evidence_root, run_schema)
    errors.extend(run_errors)
    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        path = f"$.edges[{index}]"
        if not isinstance(edge, dict):
            continue
        errors.extend(_artifact_errors(edge, index, evidence_root))
        edge_id = edge.get("edge_id")
        if isinstance(edge_id, str):
            if edge_id in edge_ids:
                errors.append(f"{path}.edge_id: duplicate")
            edge_ids.add(edge_id)
        run_id = edge.get("run_id")
        if isinstance(run_id, str) and run_id not in run_records:
            errors.append(f"{path}.run_id: unknown run reference {run_id!r}")
        elif isinstance(run_id, str):
            artifacts = run_records[run_id].get("artifacts")
            association = (
                artifacts.get(edge.get("artifact_path"))
                if isinstance(artifacts, dict)
                else None
            )
            if (
                not isinstance(association, dict)
                or association.get("value") != edge.get("artifact_hash")
            ):
                errors.append(
                    f"{path}.artifact_path: artifact is not associated with "
                    "referenced run"
                )
        if (
            edge.get("reviewer_decision") == "accepted"
            and edge.get("decision_source") == "agent-analysis"
        ):
            errors.append(f"{path}: agent-only accepted decision is forbidden")

    decision = graph.get("final_decision")
    if isinstance(decision, dict):
        if (
            decision.get("status") == "accepted"
            and decision.get("decision_source") == "agent-analysis"
        ):
            errors.append("$.final_decision: agent-only pass decision is forbidden")
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
    if len(args) != 3 or args[0] != "--evidence-root":
        errors = [
            "usage: validate_claim_graph.py --evidence-root <directory> "
            "<claim-graph.json>"
        ]
    else:
        try:
            evidence_root = Path(args[1]).resolve(strict=True)
            if not evidence_root.is_dir():
                raise ValueError("evidence root is not a directory")
            graph = json.loads(
                Path(args[2]).read_text(encoding="utf-8"),
                parse_constant=_reject_constant,
            )
            errors = validate(graph, evidence_root)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
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
