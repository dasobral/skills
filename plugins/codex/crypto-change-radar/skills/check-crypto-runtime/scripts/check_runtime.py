#!/usr/bin/env python3
"""Check the pinned crypto plugin runtime without changing it."""

from __future__ import annotations

import json
import sys


EXPECTED = "4.26.0"
GUIDANCE = "With user approval, run: python3 -m pip install jsonschema==4.26.0"


def main() -> None:
    try:
        import importlib.metadata

        version = importlib.metadata.version("jsonschema")
    except (ImportError, importlib.metadata.PackageNotFoundError):
        version = None
    state = "pass" if version == EXPECTED else "evidence-gap"
    result = {
        "evidence_state": state,
        "expected_version": EXPECTED,
        "installed_version": version,
        "setup_guidance": None if state == "pass" else GUIDANCE,
    }
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if state == "pass" else 3)


if __name__ == "__main__":
    main()
