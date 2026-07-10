#!/usr/bin/env python3
"""Execute an interoperability probe without a shell and record provenance."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from contract_utils import reject_credentials, validate_contract
from record_case import build_record


OBSERVED_FIELDS = {
    "negotiated_result",
    "sizes_bytes",
    "latency_ms",
    "fragmentation",
    "negative_tests",
    "evidence_hashes",
}


def _hash(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _normalized_policy(runner: dict[str, object]) -> dict[str, object]:
    policy = runner.get("policy")
    if not isinstance(policy, dict):
        policy = {}
    sandbox_profile = policy.get("sandbox_profile")
    return {
        "executable": policy.get("executable"),
        "executable_sha256": policy.get("executable_sha256"),
        "workdir_policy": policy.get("workdir_policy"),
        "sandbox_profile": (
            sandbox_profile
            if sandbox_profile == "bubblewrap-full-isolation"
            else None
        ),
        "approved_inputs": policy.get("approved_inputs", []),
    }


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            return True
    return False


def _trusted_bwrap() -> Path | None:
    path = Path("/usr/bin/bwrap")
    try:
        metadata = path.stat()
        resolved = path.resolve(strict=True)
    except OSError:
        return None
    if (
        resolved != path
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & 0o022
        or not os.access(path, os.X_OK)
    ):
        return None
    return path


def _safe_command(
    argv: list[str], policy: dict[str, object], output_directory: Path
) -> tuple[list[str] | None, str | None]:
    executable = Path(argv[0]).expanduser()
    try:
        resolved = executable.resolve(strict=True)
    except OSError:
        return None, "approved executable is unavailable"
    if _has_symlink_component(executable.absolute()) or not resolved.is_file():
        return None, "approved executable must be a regular non-symlink file"
    if policy["executable"] != str(resolved):
        return None, "runner executable does not match the pinned policy"
    if policy["executable_sha256"] != _hash(resolved.read_bytes()):
        return None, "runner executable hash does not match the pinned policy"
    try:
        resolved.relative_to("/usr")
    except ValueError:
        return None, "approved executable must be within the minimal /usr runtime"
    if policy["workdir_policy"] != "isolated-temporary-directory":
        return None, "isolated temporary workdir policy is required"
    if policy["sandbox_profile"] != "bubblewrap-full-isolation":
        return None, "bubblewrap full-isolation sandbox profile is required"
    inputs = policy.get("approved_inputs")
    if not isinstance(inputs, list):
        return None, "approved fixture inputs must be an array"
    bindings: list[tuple[Path, str]] = []
    approved_sandbox_paths: set[str] = set()
    for item in inputs:
        if not isinstance(item, dict) or set(item) != {
            "host_path",
            "sandbox_path",
            "sha256",
        }:
            return None, "approved fixture input record is invalid"
        host_raw = item.get("host_path")
        sandbox_path = item.get("sandbox_path")
        if (
            not isinstance(host_raw, str)
            or not isinstance(sandbox_path, str)
            or not re.fullmatch(r"/inputs/[A-Za-z0-9._-]+", sandbox_path)
        ):
            return None, "approved fixture input path is invalid"
        host = Path(host_raw).expanduser()
        try:
            host_resolved = host.resolve(strict=True)
        except OSError:
            return None, "approved fixture input is unavailable"
        if (
            _has_symlink_component(host.absolute())
            or not host_resolved.is_file()
            or item.get("sha256") != _hash(host_resolved.read_bytes())
            or sandbox_path in approved_sandbox_paths
        ):
            return None, "approved fixture input failed integrity checks"
        bindings.append((host_resolved, sandbox_path))
        approved_sandbox_paths.add(sandbox_path)
    for argument in argv[1:]:
        if argument.startswith("/") and argument not in approved_sandbox_paths:
            return None, "absolute input arguments must name an approved fixture"
    bwrap = _trusted_bwrap()
    if bwrap is None:
        return None, "trusted bubblewrap at /usr/bin/bwrap is unavailable; execution refused"
    command = [
        bwrap,
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--cap-drop",
        "ALL",
        "--clearenv",
        "--tmpfs",
        "/",
        "--dir",
        "/usr",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--tmpfs",
        "/tmp",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/work",
        "--dir",
        "/inputs",
        "--bind",
        str(output_directory),
        "/output",
    ]
    for host, sandbox_path in bindings:
        command.extend(["--ro-bind", str(host), sandbox_path])
    command.extend(
        [
            "--remount-ro",
            "/",
            "--chdir",
            "/work",
            "--",
            str(resolved),
            *argv[1:],
        ]
    )
    return command, None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        reject_credentials(payload)
        runner = payload["runner"]
        argv = runner["argv"]
        timeout = runner["timeout_seconds"]
        if not isinstance(argv, list) or not argv or not all(
            isinstance(part, str) and part for part in argv
        ):
            raise ValueError("runner.argv must be a non-empty string array")
        policy = _normalized_policy(runner)
        observed = None
        with tempfile.TemporaryDirectory(prefix="crypto-interop-") as temporary:
            output_directory = Path(temporary) / "output"
            output_directory.mkdir(mode=0o700)
            command, refusal = _safe_command(argv, policy, output_directory)
            if command is None:
                execution = {
                    "evidence_state": "evidence-gap",
                    "exit_code": None,
                    "stdout_hash": None,
                    "stderr_hash": None,
                    "sandbox_profile": policy["sandbox_profile"],
                    "workdir_policy": policy["workdir_policy"],
                    "guidance": (
                        f"{refusal}; configure an explicit safe sandbox policy"
                    ),
                }
            else:
                try:
                    completed = subprocess.run(
                        command,
                        shell=False,
                        cwd=output_directory,
                        env={},
                        capture_output=True,
                        timeout=timeout,
                        check=False,
                    )
                    state = "pass" if completed.returncode == 0 else "fail"
                    sandbox_error = completed.stderr.lower()
                    if completed.returncode != 0 and any(
                        marker in sandbox_error
                        for marker in (
                            b"operation not permitted",
                            b"creating new namespace failed",
                            b"setting up uid map",
                        )
                    ):
                        state = "evidence-gap"
                    execution = {
                        "evidence_state": state,
                        "exit_code": completed.returncode,
                        "stdout_hash": _hash(completed.stdout),
                        "stderr_hash": _hash(completed.stderr),
                        "sandbox_profile": policy["sandbox_profile"],
                        "workdir_policy": policy["workdir_policy"],
                        "guidance": (
                            "bubblewrap full isolation unavailable on this host"
                            if state == "evidence-gap"
                            else None
                        ),
                    }
                    if completed.returncode == 0:
                        try:
                            observed = json.loads(completed.stdout)
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            observed = None
                            execution["evidence_state"] = "fail"
                        if not isinstance(observed, dict):
                            execution["evidence_state"] = "fail"
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    execution = {
                        "evidence_state": "evidence-gap",
                        "exit_code": None,
                        "stdout_hash": None,
                        "stderr_hash": None,
                        "sandbox_profile": policy["sandbox_profile"],
                        "workdir_policy": policy["workdir_policy"],
                        "guidance": "bubblewrap full isolation was unavailable",
                    }
        candidate = dict(payload["case"])
        if execution["evidence_state"] == "pass":
            candidate.update(
                {
                    key: observed[key]
                    for key in sorted(OBSERVED_FIELDS)
                    if key in observed
                }
            )
        else:
            candidate["evidence_state"] = execution["evidence_state"]
        record = build_record(candidate)
        result = {
            "schema_version": "1.0",
            "runner": {
                "argv": argv,
                "timeout_seconds": timeout,
                "policy": policy,
            },
            "execution": execution,
            "case_record": {
                "case_id": record["case_id"],
                "evidence_state": record["evidence_state"],
                "record_hash": record["record_hash"],
            },
        }
        validate_contract(result, "interoperability-run.schema.json")
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
