"""Detached-signature approvals with a local HMAC storage chain."""

from __future__ import annotations

import base64
import contextlib
import datetime as dt
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

KEY_FILE = "control-state.key"
LEDGER_FILE = "approval-ledger.jsonl"
LOCK_FILE = "control-state.lock"
GENESIS_HMAC = "hmac-sha256:" + ("0" * 64)
GENESIS_HASH = "sha256:" + ("0" * 64)
MAX_BYTES = 1024 * 1024
ENTRY_KEYS = {
    "schema_version",
    "sequence",
    "signed_payload",
    "signature",
    "prior_entry_hmac",
    "entry_hmac",
}
PAYLOAD_KEYS = {
    "schema_version",
    "plugin",
    "artifact",
    "artifact_digest",
    "decision",
    "approver_id",
    "signed_at",
    "prior_entry_hash",
}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def canonical_digest(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _signature_tool() -> Path | None:
    path = Path("/usr/bin/openssl")
    try:
        metadata = path.stat()
    except OSError:
        return None
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & 0o022
        or not os.access(path, os.X_OK)
    ):
        return None
    return path


def trust_root(
    state: Path, plugin: str, environment_name: str
) -> tuple[Path | None, str]:
    prefix = environment_name.removesuffix("_TRUST_ROOT")
    boundary_raw = os.environ.get(prefix + "_TRUST_BOUNDARY")
    if not boundary_raw:
        return None, "explicit managed trust boundary is missing"
    trusted_uids = {0}
    trusted_uid_raw = os.environ.get(prefix + "_TRUSTED_UID")
    if trusted_uid_raw:
        try:
            trusted_uids.add(int(trusted_uid_raw))
        except ValueError:
            return None, "explicit trusted UID is invalid"
    boundary = Path(boundary_raw).expanduser()
    configured = os.environ.get(environment_name)
    candidate = (
        Path(configured).expanduser()
        if configured
        else boundary / f"{plugin}.pem"
    )
    try:
        boundary_absolute = boundary.absolute()
        candidate_absolute = candidate.absolute()
        if not candidate_absolute.is_relative_to(boundary_absolute):
            raise ValueError("trust root is outside the managed boundary")
        relative = candidate_absolute.relative_to(boundary_absolute)
        current = boundary_absolute
        components = [current]
        for part in relative.parts:
            current /= part
            components.append(current)
        for index, component in enumerate(components):
            metadata = component.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError("managed trust path contains a symlink")
            if metadata.st_uid not in trusted_uids:
                raise ValueError("managed trust path has an untrusted owner")
            if index < len(components) - 1:
                if not stat.S_ISDIR(metadata.st_mode):
                    raise ValueError("managed trust parent is not a directory")
                if stat.S_IMODE(metadata.st_mode) & 0o022:
                    raise ValueError("managed trust parent is group/other writable")
                if (
                    os.geteuid() != 0
                    and (
                        os.access(component, os.W_OK)
                        or (
                            metadata.st_uid == os.geteuid()
                            and stat.S_IMODE(metadata.st_mode) & 0o200
                        )
                    )
                ):
                    raise ValueError(
                        "managed trust parent permits unprivileged replacement"
                    )
        resolved = candidate.resolve(strict=True)
        metadata = candidate.lstat()
        if not resolved.is_relative_to(boundary.resolve(strict=True)):
            raise ValueError("trust root escapes the managed boundary")
    except OSError:
        return None, "external trust root is missing"
    except ValueError as error:
        return None, f"external trust root is untrusted: {error}"
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid not in trusted_uids
        or stat.S_IMODE(metadata.st_mode) & 0o222
        or resolved.stat().st_size > 64 * 1024
    ):
        return None, "external trust root is writable or untrusted"
    if _signature_tool() is None:
        return None, "detached-signature tooling is unavailable or untrusted"
    return resolved, "pass"


def _verify_signature(
    root: Path, payload: dict[str, object], signature: bytes
) -> bool:
    tool = _signature_tool()
    if tool is None:
        return False
    with tempfile.TemporaryDirectory(prefix="control-signature-") as temporary:
        payload_path = Path(temporary) / "payload.json"
        signature_path = Path(temporary) / "signature.bin"
        payload_path.write_bytes(_canonical(payload))
        signature_path.write_bytes(signature)
        completed = subprocess.run(
            [
                str(tool),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(root),
                "-rawin",
                "-in",
                str(payload_path),
                "-sigfile",
                str(signature_path),
            ],
            shell=False,
            env={},
            capture_output=True,
            timeout=5,
            check=False,
        )
    return completed.returncode == 0


def _entry_hmac(key: bytes, entry: dict[str, object]) -> str:
    unsigned = {name: value for name, value in entry.items() if name != "entry_hmac"}
    return "hmac-sha256:" + hmac.new(
        key, _canonical(unsigned), hashlib.sha256
    ).hexdigest()


def _read(path: Path, maximum: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise ValueError(f"{path.name} must be a mode 0600 regular file")
        data = os.read(descriptor, maximum + 1)
        if len(data) > maximum:
            raise ValueError(f"{path.name} exceeds its size limit")
        return data
    finally:
        os.close(descriptor)


@contextlib.contextmanager
def _lock(state: Path, *, create: bool, exclusive: bool) -> Iterator[None]:
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    if create:
        flags |= os.O_CREAT
    descriptor = os.open(state / LOCK_FILE, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise ValueError("control-state lock must be a mode 0600 regular file")
        fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _key(state: Path, *, create: bool) -> bytes:
    path = state / KEY_FILE
    if create and not path.exists():
        descriptor = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            os.write(descriptor, secrets.token_bytes(32))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    key = _read(path, 64)
    if len(key) != 32:
        raise ValueError("local HMAC storage key must contain exactly 32 bytes")
    return key


def _valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None


def signing_payload(
    plugin: str,
    artifact: str,
    artifact_digest: str,
    approver_id: str,
    signed_at: str,
    previous: dict[str, object] | None,
) -> dict[str, object]:
    if not approver_id.strip() or not _valid_timestamp(signed_at):
        raise ValueError("approver identity and UTC signed timestamp are required")
    return {
        "schema_version": "1.0",
        "plugin": plugin,
        "artifact": artifact,
        "artifact_digest": artifact_digest,
        "decision": "approve",
        "approver_id": approver_id,
        "signed_at": signed_at,
        "prior_entry_hash": canonical_digest(previous) if previous else GENESIS_HASH,
    }


def _entries(
    state: Path,
    key: bytes,
    root: Path,
    plugin: str,
    *,
    missing_ok: bool,
) -> list[dict[str, object]]:
    path = state / LEDGER_FILE
    if missing_ok and not path.exists():
        return []
    prior_hmac = GENESIS_HMAC
    previous: dict[str, object] | None = None
    entries: list[dict[str, object]] = []
    for sequence, line in enumerate(_read(path, MAX_BYTES).splitlines(), start=1):
        try:
            entry = json.loads(line)
            payload = entry["signed_payload"]
            signature = base64.b64decode(entry["signature"], validate=True)
        except (
            KeyError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
        ):
            raise ValueError("authenticated approval ledger is malformed") from None
        if (
            not isinstance(entry, dict)
            or set(entry) != ENTRY_KEYS
            or entry.get("schema_version") != "1.0"
            or entry.get("sequence") != sequence
            or not isinstance(payload, dict)
            or set(payload) != PAYLOAD_KEYS
            or payload.get("plugin") != plugin
            or payload.get("decision") not in {"approve", "deny"}
            or not isinstance(payload.get("approver_id"), str)
            or not payload["approver_id"]
            or not _valid_timestamp(payload.get("signed_at"))
            or payload.get("prior_entry_hash")
            != (canonical_digest(previous) if previous else GENESIS_HASH)
            or entry.get("prior_entry_hmac") != prior_hmac
            or not _verify_signature(root, payload, signature)
            or not hmac.compare_digest(
                str(entry.get("entry_hmac", "")), _entry_hmac(key, entry)
            )
        ):
            raise ValueError(
                "authenticated approval signature, HMAC, or chain is invalid"
            )
        prior_hmac = str(entry["entry_hmac"])
        previous = entry
        entries.append(entry)
    if not entries and not missing_ok:
        raise ValueError("authenticated approval ledger is missing or empty")
    return entries


def previous_entry(
    state: Path, root: Path, plugin: str
) -> dict[str, object] | None:
    if not state.exists():
        return None
    with _lock(state, create=False, exclusive=False):
        entries = _entries(
            state, _key(state, create=False), root, plugin, missing_ok=True
        )
        return entries[-1] if entries else None


def append_signed_approval(
    state: Path,
    plugin: str,
    artifact_name: str,
    artifact_value: object,
    payload: dict[str, object],
    signature: bytes,
    root: Path,
) -> dict[str, object]:
    if not _verify_signature(root, payload, signature):
        raise ValueError("detached approval signature verification failed")
    if state.is_symlink():
        raise ValueError("external state directory must not be a symlink")
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(state.stat().st_mode) != 0o700:
        raise ValueError("external state directory must have mode 0700")
    with _lock(state, create=True, exclusive=True):
        ledger_exists = (state / LEDGER_FILE).exists()
        if ledger_exists:
            key = _key(state, create=False)
            entries = _entries(state, key, root, plugin, missing_ok=True)
        else:
            entries = []
        expected = signing_payload(
            plugin,
            artifact_name,
            canonical_digest(artifact_value),
            str(payload.get("approver_id", "")),
            str(payload.get("signed_at", "")),
            entries[-1] if entries else None,
        )
        if payload != expected:
            raise ValueError("signed approval payload does not match current state")
        if not ledger_exists:
            key = _key(state, create=True)
        entry: dict[str, object] = {
            "schema_version": "1.0",
            "sequence": len(entries) + 1,
            "signed_payload": payload,
            "signature": base64.b64encode(signature).decode("ascii"),
            "prior_entry_hmac": (
                str(entries[-1]["entry_hmac"]) if entries else GENESIS_HMAC
            ),
        }
        entry["entry_hmac"] = _entry_hmac(key, entry)
        _write_artifact(state / artifact_name, artifact_value)
        descriptor = os.open(
            state / LEDGER_FILE,
            os.O_WRONLY
            | os.O_APPEND
            | os.O_CREAT
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            os.write(descriptor, _canonical(entry) + b"\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return entry


def _write_artifact(path: Path, value: object) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def verify_approval(
    state: Path, plugin: str, artifact_name: str, root: Path
) -> tuple[dict[str, object] | None, str]:
    try:
        if (
            not state.is_dir()
            or state.is_symlink()
            or stat.S_IMODE(state.stat().st_mode) != 0o700
        ):
            raise ValueError("authenticated external state is missing or unsafe")
        with _lock(state, create=False, exclusive=False):
            entries = _entries(
                state, _key(state, create=False), root, plugin, missing_ok=False
            )
            approvals = [
                entry
                for entry in entries
                if entry["signed_payload"]["artifact"] == artifact_name
            ]
            if (
                not approvals
                or approvals[-1]["signed_payload"]["decision"] != "approve"
            ):
                raise ValueError("authenticated approval decision is missing or denied")
            artifact = json.loads(_read(state / artifact_name, MAX_BYTES))
            if approvals[-1]["signed_payload"]["artifact_digest"] != canonical_digest(
                artifact
            ):
                raise ValueError(
                    "authenticated approval does not match the control artifact"
                )
            return artifact, "pass"
    except (
        OSError,
        subprocess.SubprocessError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        return None, f"fail: authenticated external state invalid: {error}"
