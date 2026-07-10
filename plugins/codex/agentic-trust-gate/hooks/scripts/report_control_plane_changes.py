#!/usr/bin/env python3
"""Report hashes of changed control-plane files without reading content aloud."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


MAX_RECORDS = 100
EXACT_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".mcp.json",
    "mcp.json",
    "package.json",
    "Makefile",
    "Justfile",
}
CONTROL_PARTS = {
    ".cursor",
    ".codex",
    ".claude",
    ".devcontainer",
    ".vscode",
    "hooks",
    "skills",
}


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


def _is_control_path(relative: Path) -> bool:
    return relative.name in EXACT_NAMES or bool(CONTROL_PARTS.intersection(relative.parts))


def _git_changed(root: Path) -> set[Path]:
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
        for raw in result.stdout.split(b"\0"):
            if raw:
                paths.add(Path(os.fsdecode(raw)))
    return paths


def _candidate_paths(root: Path, versioned: bool) -> list[Path]:
    if versioned:
        relative_paths = _git_changed(root)
    else:
        relative_paths = {
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() or path.is_symlink()
        }
    return sorted(
        (path for path in relative_paths if _is_control_path(path)),
        key=lambda path: path.as_posix(),
    )


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
    records = []
    for relative in _candidate_paths(root, git_root is not None)[:MAX_RECORDS]:
        content_hash = _hash(root / relative)
        if content_hash:
            records.append(f"{relative.as_posix()}={content_hash}")
    if not records:
        return
    truncated = " (truncated)" if len(records) == MAX_RECORDS else ""
    context = (
        "Changed control-plane file hashes"
        f"{truncated}: {', '.join(records)}. Review trust before execution; "
        "this reminder is not an enforcement boundary."
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
