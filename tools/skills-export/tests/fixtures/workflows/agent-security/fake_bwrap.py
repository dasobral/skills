#!/usr/bin/env python3
"""Test-only bubblewrap protocol shim; it records and translates bind paths."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    arguments = sys.argv[1:]
    Path(__file__).with_name("last-bwrap-args.json").write_text(
        json.dumps(arguments), encoding="utf-8"
    )
    bindings: dict[str, str] = {}
    working_directory: str | None = None
    index = 0
    one_argument = {"--dir", "--tmpfs", "--proc", "--dev"}
    no_argument = {
        "--unshare-all",
        "--unshare-net",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--unshare-cgroup",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
    }
    while arguments[index] != "--":
        option = arguments[index]
        if option in {"--ro-bind", "--bind"}:
            bindings[arguments[index + 2]] = arguments[index + 1]
            index += 3
        elif option == "--chdir":
            working_directory = arguments[index + 1]
            index += 2
        elif option in one_argument:
            index += 2
        elif option == "--setenv":
            index += 3
        elif option == "--cap-drop":
            index += 2
        elif option in no_argument:
            index += 1
        else:
            raise SystemExit(f"unsupported fake bwrap option: {option}")
    command = arguments[index + 1 :]

    def translate(value: str) -> str:
        if value in bindings:
            return bindings[value]
        for guest, host in sorted(
            bindings.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if value.startswith(guest + "/"):
                return host + value[len(guest) :]
        return value

    completed = subprocess.run(
        [translate(value) for value in command],
        cwd=translate(working_directory) if working_directory else None,
        env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
    )
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
