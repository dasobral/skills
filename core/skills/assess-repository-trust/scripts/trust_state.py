"""Authenticated external state for repository trust snapshots."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import stat
from pathlib import Path
from typing import Any, BinaryIO, Callable


KEY_NAME = "trust.key"
LEDGER_NAME = "trust-ledger.jsonl"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def _authenticate(key: bytes, label: str, value: object) -> str:
    return "hmac-sha256:" + hmac.new(
        key, label.encode() + b"\0" + _canonical(value), hashlib.sha256
    ).hexdigest()


def resolve_state_dir(explicit: Path | None) -> Path:
    value = explicit or (
        Path(os.environ["PLUGIN_DATA"]) if os.environ.get("PLUGIN_DATA") else None
    )
    if value is None:
        raise ValueError("authenticated external state is required")
    return value.expanduser().resolve()


def _check_file(path: Path) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"unsafe trust state file: {path.name}")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError(f"trust state file must be chmod 600: {path.name}")


def initialize_key(state_dir: Path) -> bytes:
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state_dir.is_symlink() or not state_dir.is_dir():
        raise ValueError("unsafe trust state directory")
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
    key = os.urandom(32)
    try:
        os.write(descriptor, key)
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o600)
    finally:
        os.close(descriptor)
    return key


def load_key(state_dir: Path) -> bytes:
    path = state_dir / KEY_NAME
    _check_file(path)
    key = path.read_bytes()
    if len(key) != 32:
        raise ValueError("trust HMAC key has invalid length")
    return key


def _anchor_path(state_dir: Path, raw: str, *, create: bool) -> Path:
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts or not relative.name:
        raise ValueError("trust anchor must remain inside external state")
    path = (state_dir / relative).resolve()
    if not path.is_relative_to(state_dir.resolve()):
        raise ValueError("trust anchor escapes external state")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    elif not path.parent.is_dir():
        raise ValueError("trust anchor parent is missing")
    return path


def _read_entries(
    stream: BinaryIO,
    key: bytes,
    schema_check: Callable[[dict[str, Any]], list[str]] | None = None,
) -> list[dict[str, Any]]:
    stream.seek(0)
    entries = [
        json.loads(line)
        for line in stream.read().decode("utf-8").splitlines()
        if line
    ]
    previous = _authenticate(key, "trust-ledger-genesis", {"ledger": "genesis"})
    for index, entry in enumerate(entries):
        if schema_check is not None:
            errors = schema_check(entry)
            if errors:
                raise ValueError(errors[0])
        if entry.get("sequence") != index + 1:
            raise ValueError("trust ledger sequence mismatch")
        if entry.get("previous_entry_hmac") != previous:
            raise ValueError("trust ledger previous-entry HMAC mismatch")
        candidate = dict(entry)
        actual = candidate.pop("entry_hmac", None)
        expected = _authenticate(key, "trust-ledger-entry", candidate)
        if not hmac.compare_digest(str(actual), expected):
            raise ValueError("trust ledger entry HMAC mismatch")
        previous = str(actual)
    return entries


def append_record(
    state_dir: Path,
    *,
    artifact_hash: str,
    binding_hash: str,
    applicability_hash: str,
    prior_snapshot_hash: str | None,
    decision: str,
    policy: dict[str, Any],
    approver: dict[str, Any],
    anchor_name: str,
    entry_schema_check: Callable[[dict[str, Any]], list[str]],
    anchor_schema_check: Callable[[dict[str, Any]], list[str]],
) -> dict[str, Any]:
    key = initialize_key(state_dir)
    anchor_path = _anchor_path(state_dir, anchor_name, create=True)
    try:
        anchor_descriptor = os.open(
            anchor_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except FileExistsError as exc:
        raise ValueError("create-only trust anchor already exists") from exc
    ledger_path = state_dir / LEDGER_NAME
    try:
        descriptor = os.open(
            ledger_path,
            os.O_RDWR
            | os.O_APPEND
            | os.O_CREAT
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "r+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            entries = _read_entries(stream, key, entry_schema_check)
            previous = (
                entries[-1]["entry_hmac"]
                if entries
                else _authenticate(
                    key, "trust-ledger-genesis", {"ledger": "genesis"}
                )
            )
            entry: dict[str, Any] = {
                "schema_version": "2.0",
                "sequence": len(entries) + 1,
                "previous_entry_hmac": previous,
                "artifact_hash": artifact_hash,
                "decision_binding_hash": binding_hash,
                "applicability_hash": applicability_hash,
                "prior_approved_snapshot_hash": prior_snapshot_hash,
                "decision": decision,
                "policy": policy,
                "approver": approver,
            }
            entry["entry_hmac"] = _authenticate(
                key, "trust-ledger-entry", entry
            )
            errors = entry_schema_check(entry)
            if errors:
                raise ValueError(errors[0])
            stream.seek(0, os.SEEK_END)
            stream.write(_canonical(entry) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        anchor: dict[str, Any] = {
            "schema_version": "1.0",
            "ledger_sequence": entry["sequence"],
            "entry_hmac": entry["entry_hmac"],
            "artifact_hash": artifact_hash,
            "decision_binding_hash": binding_hash,
            "applicability_hash": applicability_hash,
        }
        anchor["anchor_hmac"] = _authenticate(key, "trust-anchor", anchor)
        errors = anchor_schema_check(anchor)
        if errors:
            raise ValueError(errors[0])
        with os.fdopen(anchor_descriptor, "wb", closefd=False) as stream:
            stream.write(json.dumps(anchor, indent=2, sort_keys=True).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.close(anchor_descriptor)
        anchor_descriptor = -1
        return entry
    except Exception:
        if anchor_descriptor >= 0:
            os.close(anchor_descriptor)
            try:
                anchor_path.unlink()
            except FileNotFoundError:
                pass
        raise


def authenticate_snapshot(
    state_dir: Path,
    *,
    anchor_name: str,
    artifact_hash: str,
    binding_hash: str,
    applicability_hash: str,
    entry_schema_check: Callable[[dict[str, Any]], list[str]],
    anchor_schema_check: Callable[[dict[str, Any]], list[str]],
) -> tuple[bool, str | None]:
    try:
        key = load_key(state_dir)
        anchor_path = _anchor_path(state_dir, anchor_name, create=False)
        _check_file(anchor_path)
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        errors = anchor_schema_check(anchor)
        if errors:
            raise ValueError(errors[0])
        candidate = dict(anchor)
        actual = candidate.pop("anchor_hmac", None)
        expected = _authenticate(key, "trust-anchor", candidate)
        if not hmac.compare_digest(str(actual), expected):
            raise ValueError("trust anchor HMAC mismatch")
        ledger_path = state_dir / LEDGER_NAME
        _check_file(ledger_path)
        with ledger_path.open("r+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            entries = _read_entries(stream, key, entry_schema_check)
        sequence = anchor["ledger_sequence"]
        if sequence < 1 or sequence > len(entries):
            raise ValueError("trust anchor ledger linkage is invalid")
        entry = entries[sequence - 1]
        if (
            anchor["entry_hmac"] != entry["entry_hmac"]
            or anchor["artifact_hash"] != artifact_hash
            or entry["artifact_hash"] != artifact_hash
            or anchor["decision_binding_hash"] != binding_hash
            or entry["decision_binding_hash"] != binding_hash
            or anchor["applicability_hash"] != applicability_hash
            or entry["applicability_hash"] != applicability_hash
            or entry["decision"] != "allow"
        ):
            raise ValueError("trust anchor does not exactly link approved snapshot")
        if any(
            later["applicability_hash"] == applicability_hash
            for later in entries[sequence:]
        ):
            raise ValueError(
                "referenced allow is not the latest applicable ledger entry"
            )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return False, str(exc)
    return True, None


def verify_ledger(
    state_dir: Path,
    schema_check: Callable[[dict[str, Any]], list[str]],
) -> dict[str, object]:
    try:
        key = load_key(state_dir)
        path = state_dir / LEDGER_NAME
        _check_file(path)
        with path.open("r+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            entries = _read_entries(stream, key, schema_check)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return {"valid": False, "entries": 0, "error": str(exc)}
    return {"valid": True, "entries": len(entries)}
