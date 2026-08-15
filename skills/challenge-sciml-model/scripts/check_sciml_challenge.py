#!/usr/bin/env python3
"""Apply deterministic SciML contract checks without deciding model adequacy."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:
    Draft202012Validator = None  # type: ignore[assignment,misc]


REQUIRED_CHECKS = (
    "grouped_regime_splits",
    "preprocessing_leakage",
    "extrapolation",
    "conservation",
    "invariance",
    "positivity",
    "boundary_conditions",
    "residual_vs_solution_error",
    "uncertainty_coverage_sharpness",
    "seed_sensitivity",
    "matched_error_baselines",
    "total_cost",
)
STATUSES = {"pass", "fail", "unknown", "not-applicable", "evidence-gap"}
SCHEMA_PATH = (
    Path(__file__).parents[1] / "references" / "sciml-challenge-result.schema.json"
)
DEPENDENCY_GUIDANCE = (
    "evidence-gap: Draft 2020-12 validation unavailable; install jsonschema "
    "(for example: python3 -m pip install jsonschema) and rerun."
)


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _format_path(parts: Any) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def evaluate(result: Any) -> tuple[str, list[str], list[str]]:
    if Draft202012Validator is None:
        return "evidence-gap", [], [DEPENDENCY_GUIDANCE]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    schema_errors = sorted(
        {
            f"{_format_path(error.absolute_path)}: {error.message}"
            for error in Draft202012Validator(schema).iter_errors(result)
        }
    )
    if schema_errors:
        return "block", schema_errors, []
    if not isinstance(result, dict):
        return "block", ["$: expected an object"], []
    blockers: list[str] = []
    findings: list[str] = []
    calibration = result.get("calibration_partitions")
    validation = result.get("validation_partitions")
    if not isinstance(calibration, list) or not isinstance(validation, list):
        blockers.append("partition identities must be arrays")
    else:
        overlap = sorted(set(calibration) & set(validation))
        if overlap:
            blockers.append(
                "forbidden calibration/validation overlap: " + ", ".join(overlap)
            )

    checks = result.get("checks")
    if not isinstance(checks, dict):
        blockers.append("checks must be an object")
        checks = {}
    for name in REQUIRED_CHECKS:
        check = checks.get(name)
        if not isinstance(check, dict):
            blockers.append(f"missing check: {name}")
            continue
        status = check.get("status")
        if status not in STATUSES:
            blockers.append(f"invalid status for {name}")
            continue
        if status == "fail" and check.get("declared_invariant") is True:
            blockers.append(f"declared invariant failure: {name}")
        elif status in {"fail", "unknown", "evidence-gap"}:
            findings.append(f"{name}: {status}")

    adequacy = result.get("model_adequacy")
    if not isinstance(adequacy, dict) or adequacy.get("finding") not in {
        "adequate",
        "inadequate",
        "uncertain",
    }:
        findings.append("model adequacy requires review")
    elif adequacy["finding"] != "adequate":
        findings.append(f"model adequacy: {adequacy['finding']}")

    if blockers:
        return "block", sorted(set(blockers)), sorted(set(findings))
    if findings:
        return "review-required", [], sorted(set(findings))
    return "contract-clear", [], []


def main() -> int:
    if Draft202012Validator is None:
        print(
            json.dumps(
                {"errors": [DEPENDENCY_GUIDANCE], "status": "evidence-gap"},
                sort_keys=True,
            )
        )
        return 1
    if len(sys.argv) != 2:
        decision, blockers, findings = (
            "block",
            ["usage: check_sciml_challenge.py <challenge-result.json>"],
            [],
        )
    else:
        try:
            result = json.loads(
                Path(sys.argv[1]).read_text(encoding="utf-8"),
                parse_constant=_reject_constant,
            )
            decision, blockers, findings = evaluate(result)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            decision, blockers, findings = "block", [f"input: {exc}"], []
    print(
        json.dumps(
            {
                "blockers": blockers,
                "decision": decision,
                "findings": findings,
                "note": "This helper does not make a scientific pass decision.",
            },
            sort_keys=True,
        )
    )
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
