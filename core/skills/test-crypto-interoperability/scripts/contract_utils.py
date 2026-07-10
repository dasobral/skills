"""Strict JSON contract and credential-field validation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

SENSITIVE = re.compile(
    r"(?:^|_)(?:access_token|api_key|authorization|bearer|client_secret|"
    r"credential|password|private_key|refresh_token|secret|seed|session_token|"
    r"symmetric_key|token)(?:_|$)"
)


def reject_credentials(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
            normalized = re.sub(r"[^a-z0-9]+", "_", camel.lower()).strip("_")
            if SENSITIVE.search(normalized):
                raise ValueError(
                    "credential-bearing field is forbidden; "
                    "secret or raw key material is forbidden"
                )
            reject_credentials(child)
    elif isinstance(value, list):
        for child in value:
            reject_credentials(child)
    elif isinstance(value, str):
        option = value.lower().replace("_", "-")
        if re.match(
            r"^--?(?:access-token|api-key|authorization|client-secret|"
            r"password|private-key|refresh-token|secret|seed|session-token|"
            r"symmetric-key|token)(?:=|$)",
            option,
        ):
            raise ValueError("credential-bearing argument is forbidden")


def validate_contract(value: object, schema_name: str) -> None:
    if Draft202012Validator is None:
        print(
            "evidence-gap: jsonschema==4.26.0 is unavailable; "
            "run the check-crypto-runtime skill for setup guidance",
            file=sys.stderr,
        )
        raise SystemExit(3)
    path = Path(__file__).resolve().parent.parent / "references" / schema_name
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "$"
        raise ValueError(f"contract validation failed at {location}")
