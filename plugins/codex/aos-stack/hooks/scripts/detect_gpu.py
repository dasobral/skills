#!/usr/bin/env python3
"""Add Codex context when a local NVIDIA GPU is available."""

from __future__ import annotations

import json
import shutil
import subprocess


def main() -> None:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return
    try:
        result = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.total",
                "--format=csv,noheader",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return
    gpu = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    if not gpu:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        f"AOS Stack GPU detected ({gpu}). Use the local-inference "
                        "skill for measured VRAM budgeting and vLLM configuration."
                    ),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
