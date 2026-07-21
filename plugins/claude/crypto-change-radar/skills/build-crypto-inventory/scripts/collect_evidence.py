#!/usr/bin/env python3
"""Collect deterministic hashes for authorized cryptographic evidence files."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from contract_utils import reject_credentials, validate_contract


ALLOWED_CLASSES = {
    "source",
    "dependency",
    "configuration",
    "binary",
    "certificate",
}
SENSITIVE_NAMES = {
    ".env",
    "credentials",
    "credentials.json",
    "secrets.json",
}
SENSITIVE_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}
PRIMITIVES = (
    ("AES-256-GCM", re.compile(rb"AES[-_ ]?256[-_ ]?GCM", re.IGNORECASE)),
    ("SHA-256", re.compile(rb"SHA[-_ ]?256|sha256", re.IGNORECASE)),
    ("ML-KEM", re.compile(rb"ML[-_ ]?KEM", re.IGNORECASE)),
    ("ML-DSA", re.compile(rb"ML[-_ ]?DSA", re.IGNORECASE)),
    ("SLH-DSA", re.compile(rb"SLH[-_ ]?DSA", re.IGNORECASE)),
    ("ECDSA", re.compile(rb"ECDSA", re.IGNORECASE)),
    ("RSA", re.compile(rb"RSA", re.IGNORECASE)),
    ("RC4", re.compile(rb"RC4", re.IGNORECASE)),
)


def _reject_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    for component in [*reversed(absolute.parents), absolute]:
        if component.is_symlink():
            raise ValueError("symlink component is forbidden")


def _is_sensitive(path: Path) -> bool:
    for part in path.parts:
        lowered = part.lower()
        if (
            lowered in SENSITIVE_NAMES
            or lowered.startswith(".env.")
            or Path(lowered).suffix in SENSITIVE_SUFFIXES
        ):
            return True
    return False


def _algorithm(content: bytes, source_class: str) -> str:
    found = [name for name, pattern in PRIMITIVES if pattern.search(content)]
    if source_class == "certificate" and not found:
        found.append("X.509")
    return "+".join(found) if found else "unknown"


def _candidate(
    *,
    source_class: str,
    relative: Path,
    content: bytes | None,
    owner: str,
) -> dict[str, object]:
    state = "pass" if content is not None else "evidence-gap"
    return {
        "asset_id": f"{source_class}:{relative.as_posix()}",
        "source_class": source_class,
        "location": relative.as_posix(),
        "algorithm": _algorithm(content, source_class) if content is not None else "unknown",
        "parameters": {},
        "mode": "unknown",
        "protocol": "unknown",
        "provider_boundary": "unknown",
        "key_purpose": "unknown",
        "fallback": "unknown",
        "owner": owner,
        "confidence": "medium" if content is not None else "low",
        "evidence_state": state,
        "evidence_hash": (
            f"sha256:{hashlib.sha256(content).hexdigest()}"
            if content is not None
            else None
        ),
    }


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        reject_credentials(payload)
        raw_root = Path(payload["root"]).expanduser().absolute()
        _reject_symlink_components(raw_root)
        if _is_sensitive(raw_root):
            raise ValueError("sensitive evidence path is forbidden")
        root = raw_root.resolve()
        if not root.is_dir():
            raise ValueError("collection root must be a directory")
        candidates = []
        for request in sorted(
            payload["requests"],
            key=lambda item: (item["source_class"], item["path"]),
        ):
            source_class = request["source_class"]
            relative = Path(request["path"])
            if source_class not in ALLOWED_CLASSES:
                raise ValueError("unsupported source_class")
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("evidence path must remain under root")
            raw_target = root / relative
            _reject_symlink_components(raw_target)
            if _is_sensitive(raw_target):
                raise ValueError("sensitive evidence path is forbidden")
            target = raw_target.resolve()
            if not target.is_relative_to(root):
                raise ValueError("evidence path escapes root")
            if _is_sensitive(target):
                raise ValueError("sensitive evidence path is forbidden")
            if target.is_file():
                content = target.read_bytes()
            else:
                content = None
            candidates.append(
                _candidate(
                    source_class=source_class,
                    relative=relative,
                    content=content,
                    owner=str(request.get("owner", "unassigned")),
                )
            )
        result = {"schema_version": "1.0", "asset_candidates": candidates}
        validate_contract(result, "evidence-collection.schema.json")
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
