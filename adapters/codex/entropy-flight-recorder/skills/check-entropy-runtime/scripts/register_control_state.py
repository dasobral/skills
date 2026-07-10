#!/usr/bin/env python3
"""Register an entropy baseline in an external HMAC-authenticated approval ledger."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts"))
from control_state import (  # noqa: E402
    append_signed_approval,
    canonical_digest,
    previous_entry,
    signing_payload,
    trust_root,
)


ARTIFACT_NAME = "entropy-baseline.json"
PLUGIN_NAME = "entropy-flight-recorder"
TRUST_ENV = "ENTROPY_FLIGHT_RECORDER_TRUST_ROOT"


def _evidence_gap(guidance: str) -> None:
    print(json.dumps({"evidence_state": "evidence-gap", "guidance": guidance}))
    raise SystemExit(3)


def _validate_artifact(artifact: object) -> None:
    script = Path(__file__).resolve()
    candidates = (
        script.parents[3]
        / "skills/qualify-entropy-source/references/entropy-baseline.schema.json",
        script.parents[6]
        / "core/skills/qualify-entropy-source/references/entropy-baseline.schema.json",
    )
    schema_path = next((path for path in candidates if path.is_file()), None)
    if schema_path is None:
        raise ValueError("entropy baseline schema is unavailable")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(artifact)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError, ValidationError):
        raise ValueError("artifact fails the strict entropy baseline schema") from None


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--approver-id", required=True)
    parser.add_argument("--signed-at", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--signature", type=Path)
    args = parser.parse_args()
    project = args.project_root.expanduser().resolve(strict=True)
    state = args.state_dir.expanduser().resolve(strict=False)
    artifact_path = args.artifact.expanduser()
    if state.is_relative_to(project):
        parser.error("state directory must be outside the project")
    if not artifact_path.is_file() or artifact_path.is_symlink():
        parser.error("artifact must be a regular non-symlink file")
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        parser.error("artifact must be readable JSON")
    try:
        _validate_artifact(artifact)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    source = artifact.get("source_identity") if isinstance(artifact, dict) else None
    if (
        not isinstance(artifact, dict)
        or set(artifact)
        != {"baseline_version", "source_identity", "source_identity_hash"}
        or not isinstance(artifact.get("baseline_version"), str)
        or not re.fullmatch(
            r"[a-z0-9_.-]+@\d{4}-\d{2}-\d{2}", artifact["baseline_version"]
        )
        or not isinstance(source, dict)
        or artifact.get("source_identity_hash") != canonical_digest(source)
    ):
        parser.error("artifact is not a strict version-pinned entropy baseline")
    root, root_state = trust_root(state, PLUGIN_NAME, TRUST_ENV)
    if root is None:
        _evidence_gap(root_state)
    try:
        prior = previous_entry(state, root, PLUGIN_NAME)
        payload = signing_payload(
            PLUGIN_NAME,
            ARTIFACT_NAME,
            canonical_digest(artifact),
            args.approver_id,
            args.signed_at,
            prior,
        )
    except (OSError, ValueError) as error:
        _evidence_gap(str(error))
    if args.prepare:
        print(json.dumps({"evidence_state": "pass", "signing_payload": payload}, sort_keys=True))
        return
    try:
        signature_path = args.signature.expanduser()
        if signature_path.is_symlink() or not signature_path.is_file():
            raise ValueError("detached signature must be a regular non-symlink file")
        entry = append_signed_approval(
            state,
            PLUGIN_NAME,
            ARTIFACT_NAME,
            artifact,
            payload,
            signature_path.read_bytes(),
            root,
        )
    except (OSError, ValueError) as error:
        _evidence_gap(str(error))
    print(
        json.dumps(
            {
                "artifact": ARTIFACT_NAME,
                "authority": "detached-signature-with-local-hmac-chain",
                "digest": canonical_digest(artifact),
                "entry_hmac": entry["entry_hmac"],
                "sequence": entry["sequence"],
                "state_dir": str(state),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
