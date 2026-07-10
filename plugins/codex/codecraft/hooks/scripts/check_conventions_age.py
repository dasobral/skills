#!/usr/bin/env python3
"""Add Codex context when repository coding conventions may be stale."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


MAX_AGE_DAYS = 30
CONVENTION_PATHS = (
    Path(".codex/CODING_REQUIREMENTS.md"),
    Path("docs/CODING_REQUIREMENTS.md"),
    Path("CODING_REQUIREMENTS.md"),
)


def _session_cwd() -> Path | None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, UnicodeError):
        return None
    raw_cwd = payload.get("cwd") if isinstance(payload, dict) else None
    if not isinstance(raw_cwd, str) or not raw_cwd.strip():
        raw_cwd = str(Path.cwd())
    try:
        cwd = Path(raw_cwd).expanduser()
        if not cwd.is_absolute():
            cwd = Path.cwd() / cwd
        cwd = cwd.resolve()
    except OSError:
        return None
    return cwd if cwd.is_dir() else None


def _repository_root(cwd: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        root = Path(result.stdout.strip()).resolve()
        if root.is_dir():
            return root
    except (OSError, subprocess.SubprocessError):
        pass
    return cwd


def main() -> None:
    cwd = _session_cwd()
    if cwd is None:
        return
    root = _repository_root(cwd)
    relative_path = next(
        (path for path in CONVENTION_PATHS if (root / path).is_file()),
        None,
    )
    if relative_path is None:
        return
    convention_file = root / relative_path
    try:
        modified_at = convention_file.stat().st_mtime
    except OSError:
        return
    age_days = max(0, int((time.time() - modified_at) / 86_400))
    if age_days <= MAX_AGE_DAYS:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        f"{relative_path.as_posix()} is {age_days} days old. "
                        "Consider running the analyze-codebase skill after recent "
                        "architectural changes."
                    ),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
