#!/usr/bin/env python3
"""Add review context for C++ tool calls containing cryptographic-risk signals."""

from __future__ import annotations

import json
import re
import sys


CPP_FILE = re.compile(r"\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)(?:\b|$)", re.IGNORECASE)
SENSITIVE_TERM = re.compile(
    r"\b(?:key|secret|password|nonce|iv|qkd|kms)\b", re.IGNORECASE
)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return
    command = tool_input.get("command", "")
    if not isinstance(command, str):
        return
    if not CPP_FILE.search(command) or not SENSITIVE_TERM.search(command):
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        "This C++ operation includes security-sensitive terms. "
                        "Run cpp-review with the security lens before finalizing "
                        "the change."
                    ),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
