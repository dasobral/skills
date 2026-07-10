#!/usr/bin/env python3
"""Validate scientific artifacts named by authentic Codex tool hook payloads."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PATCH_PATH = re.compile(
    r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$", re.MULTILINE
)
JSON_PATH = re.compile(r"""(?P<path>(?:[A-Za-z]:)?[^\s"'`]+\.json)\b""")
SCIENTIFIC_FILENAMES = {
    "run-record.json": "run",
    "unit-registry.json": "unit",
    "numerical-equivalence-result.json": "numerical",
    "uncertainty-statement.json": "uncertainty",
    "claim-evidence-graph.json": "claim",
    "sciml-challenge-result.json": "sciml",
}


def _skill_root() -> Path | None:
    plugin_root = Path(__file__).parents[2]
    generated = plugin_root / "skills"
    if generated.is_dir():
        return generated
    try:
        repository = Path(__file__).parents[5]
    except IndexError:
        return None
    authored = repository / "core" / "skills"
    return authored if authored.is_dir() else None


def _candidate_paths(
    tool_name: str, tool_input: dict[str, Any], cwd: Path
) -> tuple[list[Path], list[str], list[str]]:
    raw_paths: list[str] = []
    if tool_name in {"Write", "Edit"}:
        raw_path = tool_input.get("file_path", tool_input.get("path"))
        if isinstance(raw_path, str):
            raw_paths.append(raw_path)
    command = tool_input.get("command")
    if isinstance(command, str):
        raw_paths.extend(PATCH_PATH.findall(command))
        raw_paths.extend(
            match.group("path") for match in JSON_PATH.finditer(command)
        )
    resolved: set[Path] = set()
    failures: list[str] = []
    evidence_gaps: list[str] = []
    for raw in raw_paths:
        candidate = Path(raw.rstrip(",;:)"))
        if not candidate.is_absolute():
            candidate = cwd / candidate
        try:
            target = candidate.resolve()
        except OSError as exc:
            evidence_gaps.append(
                f"evidence-gap: {raw}: cannot resolve candidate path: {exc}"
            )
            continue
        if not target.is_relative_to(cwd):
            failures.append(f"{raw}: candidate path escapes cwd")
            continue
        resolved.add(target)
    return sorted(resolved), sorted(failures), sorted(evidence_gaps)


def _artifact_kind(value: Any, path: Path) -> str | None:
    if not isinstance(value, dict):
        return SCIENTIFIC_FILENAMES.get(path.name)
    if {"run_id", "quantity_of_interest", "results"} <= set(value):
        return "run"
    if "quantities" in value:
        return "unit"
    if {"reference_run_id", "candidate_run_id", "metric"} <= set(value):
        return "numerical"
    if {"quantity", "meaning", "coverage_probability", "interval"} <= set(value):
        return "uncertainty"
    if {"graph_id", "claim", "edges"} <= set(value):
        return "claim"
    if {"challenge_id", "model_revision", "checks"} <= set(value):
        return "sciml"
    return SCIENTIFIC_FILENAMES.get(path.name)


def _validator_command(kind: str, skills: Path, path: Path) -> list[str]:
    if kind == "run":
        script = (
            skills
            / "capture-scientific-run"
            / "scripts"
            / "validate_run_record.py"
        )
        extra: list[str] = []
    elif kind in {"unit", "numerical", "uncertainty"}:
        script = (
            skills
            / "capture-scientific-run"
            / "scripts"
            / "validate_run_record.py"
        )
        schema_name = {
            "unit": "unit-registry",
            "numerical": "numerical-equivalence-result",
            "uncertainty": "uncertainty-statement",
        }[kind]
        extra = ["--schema", schema_name]
    elif kind == "claim":
        script = (
            skills
            / "audit-scientific-claim"
            / "scripts"
            / "validate_claim_graph.py"
        )
        extra = ["--evidence-root", str(path.parent)]
    else:
        script = (
            skills
            / "challenge-sciml-model"
            / "scripts"
            / "check_sciml_challenge.py"
        )
        extra = []
    return [sys.executable, str(script), *extra, str(path)]


def _validate_artifacts(
    tool_name: str, tool_input: dict[str, Any], cwd: Path
) -> tuple[list[str], list[str]]:
    skills = _skill_root()
    if skills is None:
        return [], [
            "evidence-gap: scientific validator skills are unavailable; "
            "reinstall the plugin and rerun validation."
        ]
    failures: list[str] = []
    evidence_gaps: list[str] = []
    paths, path_failures, path_gaps = _candidate_paths(tool_name, tool_input, cwd)
    failures.extend(path_failures)
    evidence_gaps.extend(path_gaps)
    for path in paths:
        if not path.is_file():
            evidence_gaps.append(
                f"evidence-gap: {path}: candidate is not a readable file"
            )
            continue
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            evidence_gaps.append(
                f"evidence-gap: {path}: cannot read candidate artifact: {exc}"
            )
            continue
        except json.JSONDecodeError:
            if path.name in SCIENTIFIC_FILENAMES:
                failures.append(f"{path}: invalid JSON")
            continue
        kind = _artifact_kind(artifact, path)
        if kind is None:
            continue
        command = _validator_command(kind, skills, path)
        runtime = command[0]
        runtime_available = (
            Path(runtime).is_file()
            if Path(runtime).is_absolute()
            else shutil.which(runtime) is not None
        )
        script_available = len(command) < 2 or Path(command[1]).is_file()
        if not runtime_available or not script_available:
            evidence_gaps.append(
                f"evidence-gap: {path}: validator runtime is unavailable"
            )
            continue
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=4,
            )
        except subprocess.TimeoutExpired:
            evidence_gaps.append(
                f"evidence-gap: {path}: scientific validator timed out"
            )
            continue
        except (OSError, subprocess.SubprocessError) as exc:
            evidence_gaps.append(
                f"evidence-gap: {path}: validator execution failed: {exc}"
            )
            continue
        try:
            details = json.loads(completed.stdout)
        except json.JSONDecodeError:
            details = None
        if not isinstance(details, dict):
            evidence_gaps.append(
                f"evidence-gap: {path}: validator execution failed "
                "without a structured objective result"
            )
            continue
        errors = details.get("errors") or details.get("blockers") or []
        summary = "; ".join(str(error) for error in errors[:3])
        message = f"{path}: {summary or 'scientific artifact validation failed'}"
        if details.get("status") == "evidence-gap":
            evidence_gaps.append(message)
        elif (
            completed.returncode != 0
            or details.get("status") == "invalid"
            or details.get("decision") == "block"
        ):
            failures.append(message)
        elif not (
            details.get("status") == "valid"
            or details.get("decision") == "review-required"
        ):
            evidence_gaps.append(
                f"evidence-gap: {path}: validator returned an unrecognized "
                "objective result"
            )
    return sorted(failures), sorted(evidence_gaps)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return
    if not isinstance(payload, dict):
        return
    event = payload.get("hook_event_name")
    tool_name = payload.get("tool_name")
    if event != "PostToolUse":
        return
    if tool_name not in {"Bash", "Write", "Edit", "apply_patch"}:
        return
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    raw_cwd = payload.get("cwd")
    if not isinstance(raw_cwd, str):
        return
    try:
        cwd = Path(raw_cwd).resolve()
    except OSError:
        return
    failures, evidence_gaps = _validate_artifacts(tool_name, tool_input, cwd)
    if not failures and not evidence_gaps:
        return
    if not failures:
        context = "Scientific validation evidence-gap: " + " | ".join(evidence_gaps)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": context,
                    }
                },
                sort_keys=True,
            )
        )
        return
    reason = "Objective scientific artifact failure: " + " | ".join(failures)
    context = reason
    if evidence_gaps:
        context += " | Scientific validation evidence-gap: " + " | ".join(
            evidence_gaps
        )
    output = {
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        },
    }
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
