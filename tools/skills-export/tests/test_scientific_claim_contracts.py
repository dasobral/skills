from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).parents[3]
FIXTURES = Path(__file__).parent / "fixtures" / "workflows" / "science"
SKILLS = ROOT / "core" / "skills"
ADAPTER = ROOT / "adapters" / "codex" / "scientific-claim-ledger"


def _run(script: Path, fixture: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), str(FIXTURES / fixture)],
        check=False,
        capture_output=True,
        text=True,
    )


def _run_path(script: Path, path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_scientific_skills_ship_portable_contracts_and_helpers() -> None:
    expected = {
        "capture-scientific-run": {
            "run-record.schema.json",
            "unit-registry.schema.json",
            "numerical-equivalence-result.schema.json",
            "uncertainty-statement.schema.json",
        },
        "audit-scientific-claim": {"claim-evidence-graph.schema.json"},
        "challenge-sciml-model": {"sciml-challenge-result.schema.json"},
    }
    scripts = {
        "capture-scientific-run": "validate_run_record.py",
        "audit-scientific-claim": "validate_claim_graph.py",
        "challenge-sciml-model": "check_sciml_challenge.py",
    }

    for skill_name, schema_names in expected.items():
        skill = SKILLS / skill_name
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith(f"---\nname: {skill_name}\n")
        assert ".codex" not in text.lower()
        for schema_name in schema_names:
            schema = json.loads(
                (skill / "references" / schema_name).read_text(encoding="utf-8")
            )
            assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
            assert schema["additionalProperties"] is False
        assert (skill / "scripts" / scripts[skill_name]).is_file()


def test_run_record_validator_accepts_complete_fixture_deterministically() -> None:
    script = (
        SKILLS
        / "capture-scientific-run"
        / "scripts"
        / "validate_run_record.py"
    )

    first = _run(script, "valid-run-record.json")
    second = _run(script, "valid-run-record.json")

    assert first.returncode == 0, first.stderr
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == {"errors": [], "status": "valid"}


def test_run_record_validator_rejects_objective_contract_failures() -> None:
    script = (
        SKILLS
        / "capture-scientific-run"
        / "scripts"
        / "validate_run_record.py"
    )

    result = _run(script, "invalid-run-record.json")

    assert result.returncode == 1
    errors = json.loads(result.stdout)["errors"]
    assert errors == sorted(errors)
    assert any("source_revision" in error for error in errors)
    assert any("unit" in error for error in errors)
    assert any("non-finite" in error for error in errors)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda record: record.update({"unexpected": True}), "Additional properties"),
        (lambda record: record.update({"seeds": "17"}), "not of type"),
        (
            lambda record: record["runtime_settings"].update({"value": "python"}),
            "not valid",
        ),
        (
            lambda record: record.update({"reproducibility_class": "approximately"}),
            "is not one of",
        ),
        (
            lambda record: record["input_hashes"]["mesh"].update(
                {"value": "sha256:bad"}
            ),
            "not valid",
        ),
    ],
)
def test_run_validator_enforces_draft_2020_schema(
    tmp_path: Path, mutation, expected: str
) -> None:
    script = (
        SKILLS / "capture-scientific-run" / "scripts" / "validate_run_record.py"
    )
    record = json.loads(
        (FIXTURES / "valid-run-record.json").read_text(encoding="utf-8")
    )
    mutation(record)
    path = tmp_path / "adversarial-run.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    result = _run_path(script, path)

    assert result.returncode == 1
    assert expected in result.stdout


@pytest.mark.parametrize(
    ("schema_name", "fixture"),
    [
        ("unit-registry", "valid-unit-registry.json"),
        ("numerical-equivalence-result", "valid-numerical-equivalence-result.json"),
        ("uncertainty-statement", "valid-uncertainty-statement.json"),
    ],
)
def test_run_validator_validates_every_published_schema(
    schema_name: str, fixture: str
) -> None:
    script = (
        SKILLS / "capture-scientific-run" / "scripts" / "validate_run_record.py"
    )

    result = _run_path(script, FIXTURES / fixture, "--schema", schema_name)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("schema_name", "fixture", "mutation", "expected"),
    [
        (
            "unit-registry",
            "valid-unit-registry.json",
            lambda value: value.update({"extra": True}),
            "Additional properties",
        ),
        (
            "numerical-equivalence-result",
            "valid-numerical-equivalence-result.json",
            lambda value: value.update({"absolute_tolerance": -1}),
            "less than the minimum",
        ),
        (
            "uncertainty-statement",
            "valid-uncertainty-statement.json",
            lambda value: value.update({"coverage_probability": 2}),
            "greater than the maximum",
        ),
    ],
)
def test_each_auxiliary_schema_rejects_adversarial_values(
    tmp_path: Path,
    schema_name: str,
    fixture: str,
    mutation,
    expected: str,
) -> None:
    script = (
        SKILLS / "capture-scientific-run" / "scripts" / "validate_run_record.py"
    )
    value = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    mutation(value)
    path = tmp_path / fixture
    path.write_text(json.dumps(value), encoding="utf-8")

    result = _run_path(script, path, "--schema", schema_name)

    assert result.returncode == 1
    assert expected in result.stdout


def test_published_schemas_are_real_draft_2020_12() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    for schema_path in sorted(SKILLS.glob("*/references/*.schema.json")):
        if schema_path.parent.parent.name not in {
            "capture-scientific-run",
            "audit-scientific-claim",
            "challenge-sciml-model",
        }:
            continue
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)


def test_claim_graph_preserves_four_assurance_activities() -> None:
    graph = json.loads((FIXTURES / "valid-claim-graph.json").read_text(encoding="utf-8"))
    activities = {edge["assurance_activity"] for edge in graph["edges"]}
    assert activities == {
        "code-verification",
        "solution-verification",
        "model-validation",
        "uncertainty-quantification",
    }
    for edge in graph["edges"]:
        assert {
            "test_id",
            "run_id",
            "artifact_path",
            "artifact_hash",
            "acceptance_criterion",
            "reviewer_decision",
        } <= set(edge)


def test_claim_graph_validator_forbids_agent_only_pass_decisions(
    tmp_path: Path,
) -> None:
    script = (
        SKILLS
        / "audit-scientific-claim"
        / "scripts"
        / "validate_claim_graph.py"
    )
    valid_path, valid_root, _ = _write_claim_graph_with_evidence(
        tmp_path / "valid"
    )
    invalid_path, invalid_root, _ = _write_claim_graph_with_evidence(
        tmp_path / "invalid", "agent-only-pass-claim-graph.json"
    )

    valid = _run_path(
        script, valid_path, "--evidence-root", str(valid_root)
    )
    invalid = _run_path(
        script, invalid_path, "--evidence-root", str(invalid_root)
    )

    assert valid.returncode == 0, valid.stderr
    assert invalid.returncode == 1
    assert "agent-only" in invalid.stdout


def test_claim_graph_validator_rejects_schema_and_reference_attacks(
    tmp_path: Path,
) -> None:
    script = (
        SKILLS / "audit-scientific-claim" / "scripts" / "validate_claim_graph.py"
    )
    graph_path, evidence_root, graph = _write_claim_graph_with_evidence(
        tmp_path
    )
    graph["edges"][0]["artifact_hash"] = "sha256:truncated"
    graph["edges"][0]["run_id"] = "missing-run"
    graph["edges"][0]["unexpected"] = "smuggled"
    graph["runs"] = ["run-grid-001", "run-bench-001", "run-uq-001"]
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    result = _run_path(
        script, graph_path, "--evidence-root", str(evidence_root)
    )

    assert result.returncode == 1
    assert "Additional properties" in result.stdout
    assert "does not match" in result.stdout
    assert "unknown run reference" in result.stdout


def test_evidence_states_are_exact_and_distinct_from_workflow_decisions() -> None:
    states = {"pass", "fail", "unknown", "not-applicable", "evidence-gap"}
    claim_schema = json.loads(
        (
            SKILLS
            / "audit-scientific-claim"
            / "references"
            / "claim-evidence-graph.schema.json"
        ).read_text(encoding="utf-8")
    )
    sciml_schema = json.loads(
        (
            SKILLS
            / "challenge-sciml-model"
            / "references"
            / "sciml-challenge-result.schema.json"
        ).read_text(encoding="utf-8")
    )

    edge = claim_schema["properties"]["edges"]["items"]["properties"]
    assert set(edge["evidence_state"]["enum"]) == states
    assert states.isdisjoint(
        claim_schema["properties"]["final_decision"]["properties"]["status"]["enum"]
    )
    assert set(sciml_schema["$defs"]["check"]["properties"]["status"]["enum"]) == states


def test_sciml_challenge_checks_all_required_failure_modes() -> None:
    schema = json.loads(
        (
            SKILLS
            / "challenge-sciml-model"
            / "references"
            / "sciml-challenge-result.schema.json"
        ).read_text(encoding="utf-8")
    )
    required_checks = set(schema["properties"]["checks"]["required"])
    assert required_checks == {
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
    }


def test_sciml_helper_blocks_objective_overlap_but_not_model_adequacy() -> None:
    script = (
        SKILLS
        / "challenge-sciml-model"
        / "scripts"
        / "check_sciml_challenge.py"
    )

    review_only = _run(script, "review-only-sciml-challenge.json")
    overlap = _run(script, "invalid-overlap-sciml-challenge.json")

    assert review_only.returncode == 0, review_only.stderr
    assert json.loads(review_only.stdout)["decision"] == "review-required"
    assert overlap.returncode == 1
    assert json.loads(overlap.stdout)["decision"] == "block"


def test_sciml_helper_rejects_wrong_types_extras_and_invalid_states(
    tmp_path: Path,
) -> None:
    script = (
        SKILLS
        / "challenge-sciml-model"
        / "scripts"
        / "check_sciml_challenge.py"
    )
    challenge = json.loads(
        (FIXTURES / "review-only-sciml-challenge.json").read_text(encoding="utf-8")
    )
    challenge["checks"]["conservation"]["status"] = "accepted"
    challenge["checks"]["conservation"]["extra"] = True
    challenge["dataset_hashes"]["benchmark"] = 7
    path = tmp_path / "adversarial-challenge.json"
    path.write_text(json.dumps(challenge), encoding="utf-8")

    result = _run_path(script, path)

    assert result.returncode == 1
    assert "Additional properties" in result.stdout
    assert "is not one of" in result.stdout
    assert "not of type" in result.stdout


def test_codex_adapter_has_three_non_deciding_agents_and_objective_hook() -> None:
    overlay = json.loads(
        (ADAPTER / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert overlay == {"interface": {"displayName": "Scientific Claim Ledger"}}

    agents = sorted((ADAPTER / "agents").glob("*.toml"))
    assert [path.stem for path in agents] == [
        "claim-auditor",
        "numerical-verifier",
        "sciml-challenger",
    ]
    for path in agents:
        agent = tomllib.loads(path.read_text(encoding="utf-8"))
        instructions = agent["developer_instructions"].lower()
        assert "cannot make the final pass decision" in instructions
        assert "evidence" in instructions

    hooks = json.loads((ADAPTER / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert set(hooks["hooks"]) == {"PostToolUse"}
    for event in hooks["hooks"].values():
        assert event[0]["matcher"] == "^(Bash|Write|Edit|apply_patch)$"
        handler = event[0]["hooks"][0]
        assert handler["command"].startswith("python3 ${PLUGIN_ROOT}/")
        assert handler["timeout"] <= 10


def _authentic_payload(
    event: str, tool_name: str, tool_input: str | dict[str, object], cwd: Path
) -> dict[str, object]:
    payload: dict[str, object] = {
        "session_id": "session-123",
        "transcript_path": None,
        "cwd": str(cwd),
        "hook_event_name": event,
        "model": "gpt-5.6-codex",
        "turn_id": "turn-456",
        "permission_mode": "default",
        "tool_name": tool_name,
        "tool_use_id": "call-789",
        "tool_input": (
            {"command": tool_input} if isinstance(tool_input, str) else tool_input
        ),
    }
    if event == "PostToolUse":
        payload["tool_response"] = {"exit_code": 0, "output": "Done!"}
    return payload


def test_repair_of_invalid_artifact_is_not_blocked_before_or_after_patch(
    tmp_path: Path,
) -> None:
    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    artifact = tmp_path / "run-record.json"
    artifact.write_text(
        (FIXTURES / "invalid-run-record.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    patch = f"*** Update File: {artifact}\n@@\n- invalid\n+ repaired\n"
    before = _authentic_payload("PreToolUse", "apply_patch", patch, tmp_path)

    pre_result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(before),
        check=False,
        capture_output=True,
        text=True,
    )
    assert pre_result.returncode == 0
    assert pre_result.stdout == ""

    artifact.write_text(
        (FIXTURES / "valid-run-record.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    after = _authentic_payload("PostToolUse", "apply_patch", patch, tmp_path)
    post_result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(after),
        check=False,
        capture_output=True,
        text=True,
    )

    assert post_result.returncode == 0
    assert post_result.stdout == ""


@pytest.mark.parametrize(
    ("tool_name", "command_template"),
    [
        ("apply_patch", "*** Update File: {path}\n@@\n"),
        ("Bash", "python3 generate.py {path}"),
    ],
)
def test_newly_invalid_result_gets_post_tool_objective_feedback(
    tmp_path: Path, tool_name: str, command_template: str
) -> None:
    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    artifact = tmp_path / "run-record.json"
    artifact.write_text(
        (FIXTURES / "invalid-run-record.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    payload = _authentic_payload(
        "PostToolUse", tool_name, command_template.format(path=artifact), tmp_path
    )

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["decision"] == "block"
    specific = output["hookSpecificOutput"]
    assert specific["hookEventName"] == "PostToolUse"
    assert specific["additionalContext"]


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        (
            "Write",
            {
                "file_path": "{path}",
                "content": "{\"run_id\":\"invalid-result\"}",
            },
        ),
        (
            "Edit",
            {
                "file_path": "{path}",
                "old_string": "\"results\": {}",
                "new_string": "\"results\": {\"temperature\": \"NaN\"}",
            },
        ),
    ],
)
def test_native_write_and_edit_payloads_validate_resulting_artifacts(
    tmp_path: Path, tool_name: str, tool_input: dict[str, object]
) -> None:
    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    artifact = tmp_path / "run-record.json"
    artifact.write_text(
        (FIXTURES / "invalid-run-record.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    formatted_input = {
        key: value.replace("{path}", str(artifact)) if isinstance(value, str) else value
        for key, value in tool_input.items()
    }
    payload = _authentic_payload(
        "PostToolUse", tool_name, formatted_input, tmp_path
    )

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["decision"] == "block"
    assert str(artifact) in output["reason"]


def test_objective_hook_ignores_supplied_contract_and_model_adequacy(
    tmp_path: Path,
) -> None:
    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    artifact = tmp_path / "challenge.json"
    artifact.write_text(
        (FIXTURES / "review-only-sciml-challenge.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    payload = _authentic_payload(
        "PostToolUse", "Bash", f"python3 evaluate.py {artifact}", tmp_path
    )
    payload["tool_input"]["scientific_contract"] = {
        "results_finite": False,
        "model_adequacy": "inadequate",
    }

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stdout == ""


@pytest.mark.parametrize(
    ("script", "fixture"),
    [
        (
            SKILLS
            / "capture-scientific-run"
            / "scripts"
            / "validate_run_record.py",
            "valid-run-record.json",
        ),
        (
            SKILLS
            / "audit-scientific-claim"
            / "scripts"
            / "validate_claim_graph.py",
            "valid-claim-graph.json",
        ),
        (
            SKILLS
            / "challenge-sciml-model"
            / "scripts"
            / "check_sciml_challenge.py",
            "review-only-sciml-challenge.json",
        ),
    ],
)
def test_standalone_validators_report_missing_jsonschema_as_evidence_gap(
    script: Path, fixture: str
) -> None:
    completed = subprocess.run(
        [sys.executable, "-S", str(script), str(FIXTURES / fixture)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr
    output = json.loads(completed.stdout)
    assert output["status"] == "evidence-gap"
    assert "install" in " ".join(output["errors"]).lower()
    assert "jsonschema" in " ".join(output["errors"]).lower()


def test_post_hook_reports_validator_setup_gap_without_objective_block(
    tmp_path: Path,
) -> None:
    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    artifact = tmp_path / "run-record.json"
    artifact.write_text(
        (FIXTURES / "valid-run-record.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    payload = _authentic_payload(
        "PostToolUse", "Bash", f"python3 generate.py {artifact}", tmp_path
    )
    environment = os.environ.copy()
    environment["PYTHONNOUSERSITE"] = "1"

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert "decision" not in output
    context = output["hookSpecificOutput"]["additionalContext"].lower()
    assert "evidence-gap" in context
    assert "install jsonschema" in context


def test_objective_hook_blocks_malformed_named_scientific_artifact(
    tmp_path: Path,
) -> None:
    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    artifact = tmp_path / "claim-evidence-graph.json"
    artifact.write_text('{"graph_id": ', encoding="utf-8")
    payload = _authentic_payload(
        "PostToolUse", "Bash", f"python3 generate.py {artifact}", tmp_path
    )

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["decision"] == "block"
    assert "invalid JSON" in output["reason"]


@pytest.mark.parametrize("attack", ["traversal", "symlink"])
def test_objective_hook_blocks_candidate_paths_that_escape_cwd(
    tmp_path: Path, attack: str
) -> None:
    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    cwd = tmp_path / "workspace"
    cwd.mkdir()
    outside = tmp_path / "run-record.json"
    outside.write_text(
        (FIXTURES / "valid-run-record.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    if attack == "traversal":
        candidate = "../run-record.json"
    else:
        link = cwd / "run-record.json"
        link.symlink_to(outside)
        candidate = "run-record.json"
    payload = _authentic_payload(
        "PostToolUse", "Write", {"file_path": candidate, "content": "{}"}, cwd
    )

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["decision"] == "block"
    assert "escapes cwd" in output["reason"]


def test_objective_hook_reports_unreadable_scientific_candidate(
    tmp_path: Path,
) -> None:
    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    artifact = tmp_path / "run-record.json"
    artifact.mkdir()
    payload = _authentic_payload(
        "PostToolUse",
        "Write",
        {"file_path": str(artifact), "content": "{}"},
        tmp_path,
    )

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert "decision" not in output
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "evidence-gap" in context
    assert "not a readable file" in context


@pytest.mark.parametrize(
    ("runtime_failure", "expected"),
    [
        ("missing", "runtime is unavailable"),
        ("timeout", "timed out"),
        ("error", "validator execution failed"),
    ],
)
def test_objective_hook_reports_validator_runtime_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runtime_failure: str,
    expected: str,
) -> None:
    import importlib.util

    hook = ADAPTER / "hooks" / "scripts" / "objective_science_gate.py"
    spec = importlib.util.spec_from_file_location(
        f"objective_science_gate_{runtime_failure}", hook
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    artifact = tmp_path / "run-record.json"
    artifact.write_text(
        (FIXTURES / "valid-run-record.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    if runtime_failure == "missing":
        monkeypatch.setattr(
            module,
            "_validator_command",
            lambda *_args: [str(tmp_path / "missing-runtime")],
        )
    elif runtime_failure == "timeout":
        def time_out(*_args: object, **_kwargs: object) -> None:
            raise subprocess.TimeoutExpired("validator", 4)

        monkeypatch.setattr(module.subprocess, "run", time_out)
    else:
        monkeypatch.setattr(
            module.subprocess,
            "run",
            lambda *_args, **_kwargs: subprocess.CompletedProcess(
                args=["validator"],
                returncode=3,
                stdout="",
                stderr="validator crashed",
            ),
        )

    failures, gaps = module._validate_artifacts(
        "Write", {"file_path": str(artifact)}, tmp_path
    )

    assert failures == []
    assert expected in " | ".join(gaps)


def test_capture_command_is_deterministic_and_marks_missing_evidence(
    tmp_path: Path,
) -> None:
    script = (
        SKILLS / "capture-scientific-run" / "scripts" / "capture_run_record.py"
    )
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    missing_input = tmp_path / "missing-input.dat"
    common = [
        sys.executable,
        str(script),
        "--context-of-use",
        "Qualified load case.",
        "--quantity-of-interest",
        "peak temperature",
        "--unit",
        "K",
        "--dimension",
        "thermodynamic-temperature",
        "--coordinate-frame",
        "plate-fixed",
        "--acceptance-threshold",
        "420",
        "--acceptance-operator",
        "<=",
        "--result",
        "413.9",
        "--absolute-tolerance",
        "0.1",
        "--relative-tolerance",
        "0.001",
        "--seed",
        "17",
        "--input",
        str(missing_input),
        "--replay",
        "python3 run.py --case qualified",
    ]
    environment = os.environ.copy()
    environment["PATH"] = ""
    environment["CC"] = "missing-compiler"
    runs = []
    for output in (first, second):
        runs.append(
            subprocess.run(
                [*common, "--output", str(output)],
                cwd=tmp_path,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
        )

    assert all(run.returncode == 0 for run in runs), runs
    first_record = json.loads(first.read_text(encoding="utf-8"))
    second_record = json.loads(second.read_text(encoding="utf-8"))
    assert first_record == second_record
    assert first_record["source_revision"]["state"] == "evidence-gap"
    assert first_record["compiler_settings"]["state"] == "evidence-gap"
    assert first_record["input_hashes"]["missing-input.dat"]["state"] == "evidence-gap"
    assert first_record["uncertainty"]["state"] == "evidence-gap"
    assert first_record["runtime_settings"]["state"] == "pass"
    assert first_record["hardware"]["state"] == "pass"
    assert first_record["parallel_layout"]["state"] == "evidence-gap"
    assert first_record["seeds"]["value"] == [17]
    assert first_record["replay_command"]["value"]["argv"] == [
        "python3",
        "run.py",
        "--case",
        "qualified",
    ]
    validator = (
        SKILLS / "capture-scientific-run" / "scripts" / "validate_run_record.py"
    )
    validation = _run_path(validator, first)
    assert validation.returncode == 0, validation.stdout + validation.stderr


def test_run_record_identity_rejects_content_tampering(tmp_path: Path) -> None:
    validator = (
        SKILLS / "capture-scientific-run" / "scripts" / "validate_run_record.py"
    )
    record = json.loads(
        (FIXTURES / "valid-run-record.json").read_text(encoding="utf-8")
    )
    valid_path = tmp_path / "valid.json"
    valid_path.write_text(json.dumps(record), encoding="utf-8")
    tampered = copy.deepcopy(record)
    tampered["context_of_use"] = "Expanded beyond the identity-bound context."
    tampered_path = tmp_path / "tampered.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")

    valid = _run_path(validator, valid_path)
    invalid = _run_path(validator, tampered_path)

    assert valid.returncode == 0, valid.stdout
    assert invalid.returncode == 1
    assert "run_id content hash mismatch" in invalid.stdout


def _write_claim_graph_with_evidence(
    tmp_path: Path, fixture: str = "valid-claim-graph.json"
) -> tuple[Path, Path, dict[str, object]]:
    graph = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    evidence_root = tmp_path / "evidence"
    artifacts = evidence_root / "artifacts"
    runs = evidence_root / "runs"
    artifacts.mkdir(parents=True)
    runs.mkdir()
    run_references = []
    for edge in graph["edges"]:
        relative = Path("artifacts") / f"{edge['edge_id']}.json"
        content = json.dumps(
            {"edge_id": edge["edge_id"], "run_id": edge["run_id"]},
            sort_keys=True,
        ).encode()
        (evidence_root / relative).write_bytes(content)
        edge["artifact_path"] = relative.as_posix()
        edge["artifact_hash"] = f"sha256:{hashlib.sha256(content).hexdigest()}"
        run_record = json.loads(
            (FIXTURES / "valid-run-record.json").read_text(encoding="utf-8")
        )
        run_record["context_of_use"] = (
            f"{run_record['context_of_use']} Evidence edge {edge['edge_id']}."
        )
        run_record["artifacts"] = {
            relative.as_posix(): {
                "state": "pass",
                "value": edge["artifact_hash"],
                "reason": "Associated with this run.",
            }
        }
        run_record.pop("run_id", None)
        canonical = json.dumps(
            run_record,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        run_id = f"run-sha256:{hashlib.sha256(canonical).hexdigest()}"
        run_record["run_id"] = run_id
        edge["run_id"] = run_id
        run_relative = Path("runs") / f"{edge['edge_id']}.json"
        run_bytes = (
            json.dumps(run_record, indent=2, sort_keys=True) + "\n"
        ).encode()
        (evidence_root / run_relative).write_bytes(run_bytes)
        run_references.append(
            {
                "run_id": run_id,
                "run_record_path": run_relative.as_posix(),
                "run_record_hash": (
                    f"sha256:{hashlib.sha256(run_bytes).hexdigest()}"
                ),
            }
        )
    graph["runs"] = run_references
    graph_path = tmp_path / "claim-evidence-graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    return graph_path, evidence_root, graph


def test_claim_graph_resolves_contained_hash_bound_evidence(tmp_path: Path) -> None:
    script = (
        SKILLS / "audit-scientific-claim" / "scripts" / "validate_claim_graph.py"
    )
    graph_path, evidence_root, _ = _write_claim_graph_with_evidence(tmp_path)

    result = _run_path(
        script, graph_path, "--evidence-root", str(evidence_root)
    )

    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    "attack",
    [
        "escape",
        "symlink",
        "missing",
        "mismatch",
        "run-tamper",
        "unassociated",
        "caller-only-runs",
    ],
)
def test_claim_graph_rejects_unsafe_or_unbound_evidence(
    tmp_path: Path, attack: str
) -> None:
    script = (
        SKILLS / "audit-scientific-claim" / "scripts" / "validate_claim_graph.py"
    )
    graph_path, evidence_root, graph = _write_claim_graph_with_evidence(tmp_path)
    edge = graph["edges"][0]
    if attack == "escape":
        outside = tmp_path / "outside.json"
        outside.write_text("outside", encoding="utf-8")
        edge["artifact_path"] = "../outside.json"
        edge["artifact_hash"] = (
            f"sha256:{hashlib.sha256(outside.read_bytes()).hexdigest()}"
        )
    elif attack == "symlink":
        outside = tmp_path / "outside.json"
        outside.write_text("outside", encoding="utf-8")
        link = evidence_root / "artifacts" / "linked.json"
        link.symlink_to(outside)
        edge["artifact_path"] = "artifacts/linked.json"
        edge["artifact_hash"] = (
            f"sha256:{hashlib.sha256(outside.read_bytes()).hexdigest()}"
        )
    elif attack == "missing":
        edge["artifact_path"] = "artifacts/missing.json"
    elif attack == "mismatch":
        (evidence_root / edge["artifact_path"]).write_text(
            "tampered", encoding="utf-8"
        )
    elif attack == "caller-only-runs":
        graph["runs"] = [reference["run_id"] for reference in graph["runs"]]
    else:
        run_reference = graph["runs"][0]
        run_path = evidence_root / run_reference["run_record_path"]
        run_record = json.loads(run_path.read_text(encoding="utf-8"))
        if attack == "run-tamper":
            run_record["context_of_use"] = "Tampered after run identity creation."
        else:
            run_record["artifacts"] = {}
            run_record.pop("run_id")
            canonical = json.dumps(
                run_record,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            new_run_id = f"run-sha256:{hashlib.sha256(canonical).hexdigest()}"
            run_record["run_id"] = new_run_id
            run_reference["run_id"] = new_run_id
            edge["run_id"] = new_run_id
        run_bytes = (
            json.dumps(run_record, indent=2, sort_keys=True) + "\n"
        ).encode()
        run_path.write_bytes(run_bytes)
        if attack == "unassociated":
            run_reference["run_record_hash"] = (
                f"sha256:{hashlib.sha256(run_bytes).hexdigest()}"
            )
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    result = _run_path(
        script, graph_path, "--evidence-root", str(evidence_root)
    )

    assert result.returncode == 1
    expected = {
        "escape": "escapes evidence root",
        "symlink": "escapes evidence root",
        "missing": "referenced artifact is missing",
        "mismatch": "artifact SHA-256 mismatch",
        "run-tamper": "run_id content hash mismatch",
        "unassociated": "artifact is not associated with referenced run",
        "caller-only-runs": "not of type 'object'",
    }[attack]
    assert expected in result.stdout


def test_capture_redacts_credentials_and_absolute_paths(tmp_path: Path) -> None:
    script = (
        SKILLS / "capture-scientific-run" / "scripts" / "capture_run_record.py"
    )
    work = tmp_path / "work"
    work.mkdir()
    input_path = work / "private-input.dat"
    input_path.write_bytes(b"scientific input")
    sensitive_name_input = work / "api-token-file-secret.dat"
    sensitive_name_input.write_bytes(b"sensitive-name input")
    claim_artifact = work / "temperature-result.json"
    claim_artifact.write_text('{"temperature": 413.9}', encoding="utf-8")
    outside_input = tmp_path / "outside-input.dat"
    outside_input.write_bytes(b"external scientific input")
    output = work / "run-record.json"
    environment = os.environ.copy()
    environment.update(
        {
            "CC": sys.executable,
            "CFLAGS": "-O2 --api-key=compiler-secret",
            "API_TOKEN": "environment-secret",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--context-of-use",
            "Credential sanitization fixture.",
            "--quantity-of-interest",
            "temperature",
            "--unit",
            "K",
            "--dimension",
            "thermodynamic-temperature",
            "--coordinate-frame",
            "test-frame",
            "--acceptance-threshold",
            "420",
            "--acceptance-operator",
            "<=",
            "--result",
            "413.9",
            "--absolute-tolerance",
            "0.1",
            "--relative-tolerance",
            "0.001",
            "--seed",
            "17",
            "--input",
            str(input_path),
            "--input",
            "../outside-input.dat",
            "--input",
            str(sensitive_name_input),
            "--artifact",
            str(claim_artifact),
            "--replay",
            (
                f"{sys.executable} run.py --token replay-secret "
                "--password=hunter2 --input /private/location/input.dat "
                "../outside-replay.dat"
            ),
        ],
        cwd=work,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    serialized = output.read_text(encoding="utf-8")
    for forbidden in (
        "compiler-secret",
        "environment-secret",
        "replay-secret",
        "hunter2",
        "file-secret",
        str(tmp_path),
        sys.executable,
        "/private/location",
    ):
        assert forbidden not in serialized
    for secret_derived in (
        "compiler-secret",
        "environment-secret",
        "replay-secret",
        "hunter2",
        str(sensitive_name_input),
        str(tmp_path),
    ):
        assert hashlib.sha256(secret_derived.encode()).hexdigest() not in serialized
    record = json.loads(serialized)
    assert record["artifacts"]["temperature-result.json"] == {
        "state": "pass",
        "value": (
            f"sha256:{hashlib.sha256(claim_artifact.read_bytes()).hexdigest()}"
        ),
        "reason": "Artifact bytes were hashed and associated with this run.",
    }
    assert "private-input.dat" in record["input_hashes"]
    assert all(
        not Path(path).is_absolute() and ".." not in Path(path).parts
        for path in record["input_hashes"]
    )
    replay = record["replay_command"]["value"]
    assert replay["redacted_arguments"] == ["--password", "--token"]
    assert "redacted_argument_hashes" not in replay
    assert replay["executable_hash"].startswith("sha256:")
    assert all(".." not in Path(argument).parts for argument in replay["argv"])
    compiler = record["compiler_settings"]["value"]
    assert compiler["redacted_flags"] == ["--api-key"]
    assert "redacted_flag_hashes" not in compiler
    validator = (
        SKILLS / "capture-scientific-run" / "scripts" / "validate_run_record.py"
    )
    validation = _run_path(validator, output)
    assert validation.returncode == 0, validation.stdout


def test_no_secret_policy_recursively_redacts_credential_fields() -> None:
    import importlib.util

    script = (
        SKILLS / "capture-scientific-run" / "scripts" / "capture_run_record.py"
    )
    spec = importlib.util.spec_from_file_location("capture_run_record", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    sanitized = module._redact_sensitive_fields(
        {
            "outer": {
                "safe": "retained",
                "password": "nested-secret",
                "child": {
                    "api_token": "deeper-secret",
                    "redacted_token": "prefixed-secret",
                },
            }
        }
    )
    serialized = json.dumps(sanitized, sort_keys=True)

    assert "nested-secret" not in serialized
    assert "deeper-secret" not in serialized
    assert "prefixed-secret" not in serialized
    assert sanitized["outer"]["safe"] == "retained"
    assert sanitized["outer"]["redacted_fields"] == ["password"]
    assert sanitized["outer"]["child"]["redacted_fields"] == [
        "api_token",
        "redacted_token",
    ]
    assert "redacted_field_hashes" not in serialized
    assert hashlib.sha256(b"nested-secret").hexdigest() not in serialized
    assert hashlib.sha256(b"deeper-secret").hexdigest() not in serialized
