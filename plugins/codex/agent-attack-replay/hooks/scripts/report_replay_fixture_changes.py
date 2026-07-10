#!/usr/bin/env python3
"""Remind on changed replay inputs without running an evaluation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


MAX_RECORDS = 100
RELEVANT_TERMS = ("prompt", "model", "tool", "fixture", "scenario", "eval")


def _cwd() -> Path | None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, UnicodeError):
        return None
    raw = payload.get("cwd") if isinstance(payload, dict) else None
    if not isinstance(raw, str) or not raw:
        return None
    try:
        path = Path(raw).expanduser().resolve()
    except OSError:
        return None
    return path if path.is_dir() else None


def _git_root(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        root = Path(result.stdout.strip()).resolve()
        return root if root.is_dir() else None
    except (OSError, subprocess.SubprocessError):
        return None


def _changed(root: Path) -> set[Path]:
    paths: set[Path] = set()
    commands = (
        ["git", "-C", str(root), "diff", "--name-only", "-z", "HEAD"],
        ["git", "-C", str(root), "diff", "--cached", "--name-only", "-z", "HEAD"],
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"],
    )
    for command in commands:
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, timeout=2
            )
        except (OSError, subprocess.SubprocessError):
            continue
        paths.update(Path(os.fsdecode(raw)) for raw in result.stdout.split(b"\0") if raw)
    return paths


def _relevant(path: Path) -> bool:
    normalized = path.as_posix().casefold()
    return any(term in normalized for term in RELEVANT_TERMS)


def _hash(path: Path) -> str | None:
    try:
        if path.is_symlink():
            data = os.readlink(path).encode("utf-8", "surrogateescape")
            return f"sha256:{hashlib.sha256(data).hexdigest()}"
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
    except OSError:
        return None


def main() -> None:
    cwd = _cwd()
    if cwd is None:
        return
    git_root = _git_root(cwd)
    root = git_root or cwd
    candidates = (
        _changed(root)
        if git_root is not None
        else {
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() or path.is_symlink()
        }
    )
    records = []
    for relative in sorted(
        (path for path in candidates if _relevant(path)),
        key=lambda path: path.as_posix(),
    )[:MAX_RECORDS]:
        content_hash = _hash(root / relative)
        if content_hash:
            records.append(f"{relative.as_posix()}={content_hash}")
    if not records:
        return
    context = (
        f"Replay evidence inputs changed: {', '.join(records)}. "
        "Regenerate pinned scenarios and rerun explicitly when appropriate; "
        "no evaluation was started by this hook."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
