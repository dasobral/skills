#!/usr/bin/env python3
"""Capture deterministic scientific run provenance without inventing evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SENSITIVE_KEY = re.compile(
    r"(?:api[-_]?key|authorization|cookie|credential|pass(?:word|wd)?|secret|token)",
    re.IGNORECASE,
)
SAFE_ENVIRONMENT_KEYS = (
    "LANG",
    "LC_ALL",
    "OMP_NUM_THREADS",
    "TZ",
    "WORLD_SIZE",
)


def _evidence(state: str, value: Any, reason: str) -> dict[str, Any]:
    return {"state": state, "value": value, "reason": reason}


def _command_output(command: list[str], cwd: Path) -> str | None:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = completed.stdout.strip() or completed.stderr.strip()
    return output or None


def _sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return f"sha256:{digest.hexdigest()}"


def _safe_path(raw: str | Path, cwd: Path) -> str:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = cwd / path
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(cwd)
        safe_parts = [
            "redacted-path" if SENSITIVE_KEY.search(part) else part
            for part in relative.parts
        ]
        return Path(*safe_parts).as_posix()
    except ValueError:
        name = resolved.name or "path"
        if SENSITIVE_KEY.search(name):
            name = "redacted-path"
        return f"_external/{name}"


def _sanitize_tokens(
    tokens: list[str], cwd: Path
) -> tuple[list[str], list[str]]:
    sanitized: list[str] = []
    redacted_fields: list[str] = []
    redact_next: str | None = None
    for token in tokens:
        if redact_next is not None:
            sanitized.append("<redacted>")
            redacted_fields.append(redact_next)
            redact_next = None
            continue
        key, separator, value = token.partition("=")
        if SENSITIVE_KEY.search(key):
            if separator:
                sanitized.append(f"{key}=<redacted>")
                redacted_fields.append(key)
            else:
                sanitized.append(token)
                redact_next = key
            continue
        if not token.startswith("-") and (
            Path(token).is_absolute() or "/" in token or "\\" in token
        ):
            sanitized.append(_safe_path(token, cwd))
        else:
            sanitized.append(token)
    return sanitized, sorted(set(redacted_fields))


def _redact_sensitive_fields(value: Any) -> Any:
    if isinstance(value, list):
        return [_redact_sensitive_fields(item) for item in value]
    if not isinstance(value, dict):
        return value
    sanitized: dict[str, Any] = {}
    redacted_fields: list[str] = []
    for key in sorted(value):
        field_value = value[key]
        if SENSITIVE_KEY.search(key):
            redacted_fields.append(key)
            continue
        sanitized[key] = _redact_sensitive_fields(field_value)
    if redacted_fields:
        sanitized["redacted_fields"] = redacted_fields
    return sanitized


def _canonical_run_id(record: dict[str, Any]) -> str:
    canonical = json.dumps(
        record,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"run-sha256:{hashlib.sha256(canonical).hexdigest()}"


def _source_revision(cwd: Path) -> dict[str, Any]:
    revision = _command_output(["git", "rev-parse", "HEAD"], cwd)
    if revision is None:
        return _evidence(
            "evidence-gap", None, "Git revision unavailable in the capture environment."
        )
    return _evidence("pass", f"git:{revision}", "Captured with git rev-parse HEAD.")


def _input_hash(path: Path) -> dict[str, Any]:
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return _evidence("evidence-gap", None, "Input unavailable.")
    return _evidence("pass", f"sha256:{digest}", "Input bytes were hashed.")


def _artifact_hash(path: Path) -> dict[str, Any]:
    digest = _sha256_file(path)
    if digest is None:
        return _evidence("evidence-gap", None, "Artifact unavailable.")
    return _evidence(
        "pass",
        digest,
        "Artifact bytes were hashed and associated with this run.",
    )


def _compiler_settings(cwd: Path) -> dict[str, Any]:
    compiler = os.environ.get("CC", "cc")
    version = _command_output([compiler, "--version"], cwd)
    safe_compiler = _safe_path(compiler, cwd)
    if version is None:
        return _evidence(
            "evidence-gap",
            None,
            f"Compiler version unavailable for {safe_compiler!r}.",
        )
    flags, redacted = _sanitize_tokens(
        shlex.split(os.environ.get("CFLAGS", "")), cwd
    )
    executable = Path(compiler) if Path(compiler).is_absolute() else None
    if executable is None:
        discovered = shutil.which(compiler)
        executable = Path(discovered) if discovered else None
    return _evidence(
        "pass",
        {
            "command": safe_compiler,
            "command_hash": _sha256_file(executable) if executable else None,
            "flags": flags,
            "redacted_flags": redacted,
            "version": version.splitlines()[0],
        },
        "Captured from CC, CFLAGS, and the compiler version command.",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--context-of-use", required=True)
    parser.add_argument("--quantity-of-interest", required=True)
    parser.add_argument("--unit", required=True)
    parser.add_argument("--dimension", required=True)
    parser.add_argument("--coordinate-frame", required=True)
    parser.add_argument("--acceptance-threshold", required=True, type=float)
    parser.add_argument(
        "--acceptance-operator",
        required=True,
        choices=("<", "<=", ">", ">=", "=="),
    )
    parser.add_argument("--result", required=True, type=float)
    parser.add_argument("--absolute-tolerance", required=True, type=float)
    parser.add_argument("--relative-tolerance", required=True, type=float)
    parser.add_argument("--seed", action="append", type=int, default=[])
    parser.add_argument("--input", action="append", type=Path, default=[])
    parser.add_argument("--artifact", action="append", type=Path, default=[])
    parser.add_argument("--replay", required=True)
    parser.add_argument(
        "--reproducibility-class",
        choices=("bitwise", "numerically-equivalent", "scientifically-equivalent"),
        default="numerically-equivalent",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    cwd = Path.cwd().resolve()
    inputs = args.input or [cwd / "<no-input-declared>"]
    seeds = (
        _evidence("pass", args.seed, "Seeds were provided by the caller.")
        if args.seed
        else _evidence("evidence-gap", None, "No random seeds were provided.")
    )
    replay_tokens = shlex.split(args.replay)
    replay, replay_redactions = _sanitize_tokens(replay_tokens, cwd)
    replay_executable = None
    if replay_tokens:
        raw_executable = replay_tokens[0]
        discovered = (
            raw_executable
            if Path(raw_executable).is_absolute()
            else shutil.which(raw_executable)
        )
        if discovered:
            replay_executable = _sha256_file(Path(discovered))
    world_size = os.environ.get("WORLD_SIZE")
    thread_count = os.environ.get("OMP_NUM_THREADS")
    if world_size is None and thread_count is None:
        parallel_evidence = _evidence(
            "evidence-gap",
            None,
            "WORLD_SIZE and OMP_NUM_THREADS were unavailable.",
        )
    else:
        try:
            parallel = {
                "processes": int(world_size or "1"),
                "threads_per_process": int(thread_count or "1"),
            }
            parallel_evidence = _evidence(
                "pass",
                parallel,
                "Captured from WORLD_SIZE and OMP_NUM_THREADS.",
            )
        except ValueError:
            parallel_evidence = _evidence(
                "evidence-gap",
                None,
                "WORLD_SIZE or OMP_NUM_THREADS was not an integer.",
            )
    raw_environment = {
        "platform": platform.platform(),
        "python_executable": _safe_path(sys.executable, cwd),
        "python_executable_hash": _sha256_file(Path(sys.executable)),
        "variables": {
            key: os.environ[key]
            for key in SAFE_ENVIRONMENT_KEYS
            if key in os.environ
        },
        "process_environment": {
            key: value
            for key, value in os.environ.items()
            if SENSITIVE_KEY.search(key)
        },
    }
    record: dict[str, Any] = {
        "context_of_use": args.context_of_use,
        "quantity_of_interest": args.quantity_of_interest,
        "unit_registry": {
            "quantities": [
                {
                    "name": args.quantity_of_interest,
                    "unit": args.unit,
                    "dimension": args.dimension,
                    "coordinate_frame": args.coordinate_frame,
                }
            ]
        },
        "coordinate_frame": args.coordinate_frame,
        "tolerances": {
            "absolute": args.absolute_tolerance,
            "relative": args.relative_tolerance,
        },
        "uncertainty": {
            "state": "evidence-gap",
            "value": None,
            "reason": "No uncertainty statement was supplied during run capture.",
        },
        "acceptance_threshold": {
            "operator": args.acceptance_operator,
            "value": args.acceptance_threshold,
            "unit": args.unit,
        },
        "source_revision": _source_revision(cwd),
        "input_hashes": {
            _safe_path(path, cwd): _input_hash(path.resolve())
            for path in sorted(inputs)
        },
        "artifacts": {
            _safe_path(path, cwd): _artifact_hash(path.resolve())
            for path in sorted(args.artifact)
        },
        "environment": _evidence(
            "pass",
            _redact_sensitive_fields(raw_environment),
            "Captured from the active process.",
        ),
        "compiler_settings": _compiler_settings(cwd),
        "runtime_settings": _evidence(
            "pass",
            {
                "implementation": platform.python_implementation(),
                "version": platform.python_version(),
            },
            "Captured from the active Python runtime.",
        ),
        "hardware": _evidence(
            "pass",
            {
                "architecture": platform.machine() or "unknown",
                "cpu_count": os.cpu_count(),
                "processor": platform.processor() or "unknown",
            },
            "Captured from the host platform APIs.",
        ),
        "parallel_layout": parallel_evidence,
        "seeds": seeds,
        "replay_command": _evidence(
            "pass",
            {
                "argv": replay,
                "executable_hash": replay_executable,
                "redacted_arguments": replay_redactions,
            },
            "Parsed and sanitized from the caller-provided replay command.",
        ),
        "reproducibility_class": args.reproducibility_class,
        "results": {args.quantity_of_interest: args.result},
    }
    record = _redact_sensitive_fields(record)
    record["run_id"] = _canonical_run_id(record)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
