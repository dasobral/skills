"""Monitor-owned authenticated replay state."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import stat
from pathlib import Path
from typing import Any, BinaryIO, Callable


KEY_NAME = "monitor.key"
LEDGER_NAME = "trust-ledger.jsonl"
KEY_BYTES = 32


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def authenticate(key: bytes, label: str, value: object) -> str:
    material = label.encode() + b"\0" + canonical_bytes(value)
    return "hmac-sha256:" + hmac.new(key, material, hashlib.sha256).hexdigest()


def _regular_mode_600(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError(f"external state file is unsafe: {path.name}")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError(f"external state file must be chmod 600: {path.name}")


def resolve_state_dir(explicit: Path | None) -> Path:
    raw = explicit or (
        Path(os.environ["PLUGIN_DATA"]) if os.environ.get("PLUGIN_DATA") else None
    )
    if raw is None:
        raise ValueError("external state is required via --state-dir or PLUGIN_DATA")
    return raw.expanduser().resolve()


def initialize_key(state_dir: Path) -> bytes:
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state_dir.is_symlink() or not state_dir.is_dir():
        raise ValueError("external state directory is unsafe")
    state_dir.chmod(0o700)
    path = state_dir / KEY_NAME
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except FileExistsError:
        return load_key(state_dir)
    key = os.urandom(KEY_BYTES)
    try:
        os.write(descriptor, key)
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o600)
    finally:
        os.close(descriptor)
    return key


def load_key(state_dir: Path) -> bytes:
    if not state_dir.is_dir() or state_dir.is_symlink():
        raise ValueError("external state directory is missing or unsafe")
    path = state_dir / KEY_NAME
    _regular_mode_600(path)
    key = path.read_bytes()
    if len(key) != KEY_BYTES:
        raise ValueError("monitor HMAC key has invalid length")
    return key


def anchor_path(state_dir: Path, raw: str, *, create_parent: bool = False) -> Path:
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts or not relative.name:
        raise ValueError("anchor must be a relative path inside external state")
    path = (state_dir / relative).resolve()
    if not path.is_relative_to(state_dir.resolve()):
        raise ValueError("anchor escapes external state")
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    elif not path.parent.is_dir():
        raise ValueError("anchor parent is missing")
    if path.parent.is_symlink():
        raise ValueError("anchor parent is unsafe")
    return path


def reserve_anchor(state_dir: Path, raw: str) -> tuple[int, Path]:
    path = anchor_path(state_dir, raw, create_parent=True)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except FileExistsError as exc:
        raise ValueError("create-only anchor already exists") from exc
    os.fchmod(descriptor, 0o600)
    return descriptor, path


def abandon_anchor(descriptor: int, path: Path) -> None:
    try:
        os.close(descriptor)
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _binding(key: bytes, label: str, value: str) -> dict[str, str]:
    return {"hash": value, "hmac": authenticate(key, label, value)}


def bindings_for_summary(
    summary: dict[str, Any], key: bytes
) -> dict[str, object]:
    roles = {
        role: _binding(key, f"role-template:{role}", value)
        for role, value in sorted(summary["role_definition_hashes"].items())
    }
    envelopes: dict[str, dict[str, list[dict[str, str]]]] = {}
    for role, attestation in sorted(summary["worker_attestations"].items()):
        envelopes[role] = {}
        for direction in ("sent", "received"):
            values = attestation[f"{direction}_envelope_hashes"]
            envelopes[role][direction] = [
                _binding(
                    key,
                    f"worker-envelope:{role}:{direction}:{index}",
                    value,
                )
                for index, value in enumerate(values)
            ]
    observations = [
        _binding(
            key,
            f"observation:{trial['trial_id']}:{observation['sequence']}",
            observation["observation_hash"],
        )
        for trial in summary["trials"]
        for observation in trial["observations"]
    ]
    return {
        "scenario": _binding(key, "scenario", summary["scenario_hash"]),
        "role_templates": roles,
        "worker_envelopes": envelopes,
        "observations": observations,
        "summary": _binding(key, "summary", summary["summary_hash"]),
    }


def _verify_bindings(bindings: dict[str, Any], key: bytes) -> None:
    scenario = bindings["scenario"]
    if scenario["hmac"] != authenticate(key, "scenario", scenario["hash"]):
        raise ValueError("ledger HMAC mismatch for scenario")
    for role, item in bindings["role_templates"].items():
        if item["hmac"] != authenticate(
            key, f"role-template:{role}", item["hash"]
        ):
            raise ValueError("ledger HMAC mismatch for role template")
    for role, directions in bindings["worker_envelopes"].items():
        for direction, items in directions.items():
            for index, item in enumerate(items):
                if item["hmac"] != authenticate(
                    key,
                    f"worker-envelope:{role}:{direction}:{index}",
                    item["hash"],
                ):
                    raise ValueError("ledger HMAC mismatch for worker envelope")
    for item in bindings["observations"]:
        label = item["label"]
        if item["hmac"] != authenticate(key, label, item["hash"]):
            raise ValueError("ledger HMAC mismatch for observation")
    summary = bindings["summary"]
    if summary["hmac"] != authenticate(key, "summary", summary["hash"]):
        raise ValueError("ledger HMAC mismatch for summary")


def _observation_bindings_with_labels(
    summary: dict[str, Any], key: bytes
) -> list[dict[str, str]]:
    return [
        {
            **_binding(
                key,
                f"observation:{trial['trial_id']}:{observation['sequence']}",
                observation["observation_hash"],
            ),
            "label": f"observation:{trial['trial_id']}:{observation['sequence']}",
        }
        for trial in summary["trials"]
        for observation in trial["observations"]
    ]


def _entry_bindings(summary: dict[str, Any], key: bytes) -> dict[str, object]:
    bindings = bindings_for_summary(summary, key)
    bindings["observations"] = _observation_bindings_with_labels(summary, key)
    return bindings


def _read_locked_ledger(
    stream: BinaryIO,
    key: bytes,
    schema_check: Callable[[dict[str, Any]], list[str]] | None = None,
) -> list[dict[str, Any]]:
    stream.seek(0)
    raw = stream.read().decode("utf-8")
    entries = [json.loads(line) for line in raw.splitlines() if line]
    previous = authenticate(key, "ledger-genesis", {"ledger": "genesis"})
    for index, entry in enumerate(entries):
        if schema_check is not None:
            errors = schema_check(entry)
            if errors:
                raise ValueError(errors[0])
        if entry.get("sequence") != index + 1:
            raise ValueError("ledger sequence mismatch")
        if entry.get("previous_entry_hmac") != previous:
            raise ValueError("ledger HMAC previous-entry mismatch")
        bindings = entry.get("bindings")
        if not isinstance(bindings, dict):
            raise ValueError("ledger bindings are invalid")
        _verify_bindings(bindings, key)
        candidate = dict(entry)
        actual = candidate.pop("entry_hmac", None)
        expected = authenticate(key, "ledger-entry", candidate)
        if not hmac.compare_digest(str(actual), expected):
            raise ValueError("ledger HMAC entry mismatch")
        previous = str(actual)
    return entries


def append_entry(
    state_dir: Path,
    summary: dict[str, Any],
    key: bytes,
    schema_check: Callable[[dict[str, Any]], list[str]] | None = None,
) -> dict[str, Any]:
    path = state_dir / LEDGER_NAME
    descriptor = os.open(
        path,
        os.O_RDWR
        | os.O_APPEND
        | os.O_CREAT
        | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "r+b", closefd=True) as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        entries = _read_locked_ledger(stream, key, schema_check)
        if any(
            item["bindings"]["summary"]["hash"] == summary["summary_hash"]
            for item in entries
        ):
            raise ValueError("authenticated replay detected")
        previous = (
            entries[-1]["entry_hmac"]
            if entries
            else authenticate(key, "ledger-genesis", {"ledger": "genesis"})
        )
        entry: dict[str, Any] = {
            "schema_version": "1.0",
            "sequence": len(entries) + 1,
            "previous_entry_hmac": previous,
            "bindings": _entry_bindings(summary, key),
        }
        entry["entry_hmac"] = authenticate(key, "ledger-entry", entry)
        if schema_check is not None:
            errors = schema_check(entry)
            if errors:
                raise ValueError(errors[0])
        stream.seek(0, os.SEEK_END)
        stream.write(canonical_bytes(entry) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
        return entry


def finish_anchor(
    descriptor: int,
    *,
    key: bytes,
    summary: dict[str, Any],
    entry: dict[str, Any],
    schema_check: Callable[[dict[str, object]], list[str]] | None = None,
) -> dict[str, object]:
    anchor: dict[str, object] = {
        "schema_version": "2.0",
        "ledger_sequence": entry["sequence"],
        "entry_hmac": entry["entry_hmac"],
        "summary_hash": summary["summary_hash"],
    }
    anchor["anchor_hmac"] = authenticate(key, "anchor", anchor)
    if schema_check is not None:
        errors = schema_check(anchor)
        if errors:
            raise ValueError(errors[0])
    payload = json.dumps(anchor, indent=2, sort_keys=True).encode() + b"\n"
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    return anchor


def validate_external_state(
    state_dir: Path,
    anchor_name: str,
    summary: dict[str, Any],
    schema_check: Callable[[str, dict[str, Any]], list[str]] | None = None,
) -> list[str]:
    try:
        key = load_key(state_dir)
        path = anchor_path(state_dir, anchor_name)
        _regular_mode_600(path)
        anchor = json.loads(path.read_text(encoding="utf-8"))
        if schema_check is not None:
            errors = schema_check("replay-anchor.schema.json", anchor)
            if errors:
                raise ValueError(errors[0])
        candidate = dict(anchor)
        actual_anchor_hmac = candidate.pop("anchor_hmac", None)
        expected_anchor_hmac = authenticate(key, "anchor", candidate)
        if not hmac.compare_digest(str(actual_anchor_hmac), expected_anchor_hmac):
            raise ValueError("external anchor HMAC mismatch")
        ledger_path = state_dir / LEDGER_NAME
        _regular_mode_600(ledger_path)
        with ledger_path.open("r+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            entries = _read_locked_ledger(
                stream,
                key,
                (
                    (
                        lambda entry: schema_check(
                            "replay-ledger-entry.schema.json", entry
                        )
                    )
                    if schema_check is not None
                    else None
                ),
            )
        if not entries:
            raise ValueError("authenticated ledger is empty")
        entry = entries[-1]
        if anchor.get("ledger_sequence") != entry["sequence"]:
            raise ValueError("external anchor is not the latest ledger entry")
        if anchor.get("entry_hmac") != entry["entry_hmac"]:
            raise ValueError("external anchor entry mismatch")
        expected_bindings = _entry_bindings(summary, key)
        if entry["bindings"] != expected_bindings:
            raise ValueError("authenticated ledger binding mismatch")
        if anchor.get("summary_hash") != summary["summary_hash"]:
            raise ValueError("external anchor summary mismatch")
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return [str(exc)]
    return []
