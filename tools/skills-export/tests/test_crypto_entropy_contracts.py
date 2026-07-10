from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[3]
FIXTURES = Path(__file__).parent / "fixtures" / "workflows"
SKILLS = {
    "build-crypto-inventory": ("cbom.schema.json", "build_inventory.py"),
    "review-crypto-delta": ("cbom-delta.schema.json", "semantic_diff.py"),
    "plan-pqc-migration": ("pqc-queue.schema.json", "rank_assets.py"),
    "test-crypto-interoperability": (
        "interoperability-case.schema.json",
        "record_case.py",
    ),
    "qualify-entropy-source": ("qualification-run.schema.json", "qualify_run.py"),
    "review-entropy-change": (
        "requalification-decision.schema.json",
        "decide_requalification.py",
    ),
}


def _fixture(domain: str) -> dict[str, Any]:
    return json.loads((FIXTURES / domain / "contracts.json").read_text())


def _run(skill: str, script: str, payload: object) -> object:
    path = ROOT / "core" / "skills" / skill / "scripts" / script
    result = subprocess.run(
        [sys.executable, str(path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def _validate(instance: object, schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def test_crypto_helpers_emit_deterministic_schema_valid_contracts() -> None:
    data = _fixture("crypto")
    cases = [
        (
            "build-crypto-inventory",
            "build_inventory.py",
            data["cbom_before"],
            data["cbom_before"],
            "cbom.schema.json",
        ),
        (
            "review-crypto-delta",
            "semantic_diff.py",
            {"before": data["cbom_before"], "after": data["cbom_after"]},
            data["cbom_delta_expected"],
            "cbom-delta.schema.json",
        ),
        (
            "plan-pqc-migration",
            "rank_assets.py",
            data["pqc_assets"],
            data["pqc_queue_expected"],
            "pqc-queue.schema.json",
        ),
        (
            "test-crypto-interoperability",
            "record_case.py",
            data["interoperability_input"],
            data["interoperability_case_expected"],
            "interoperability-case.schema.json",
        ),
    ]
    for skill, script, payload, expected, schema_name in cases:
        first = _run(skill, script, payload)
        second = _run(skill, script, payload)
        assert first == second == expected
        schema = json.loads(
            (
                ROOT / "core" / "skills" / skill / "references" / schema_name
            ).read_text()
        )
        _validate(first, schema)


def test_inventory_rejects_secret_or_raw_key_material() -> None:
    data = _fixture("crypto")["cbom_before"]
    data["assets"][0]["private_key"] = "do-not-collect"
    script = (
        ROOT
        / "core/skills/build-crypto-inventory/scripts/build_inventory.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(data),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "secret or raw key material is forbidden" in result.stderr
    assert "do-not-collect" not in result.stderr


@pytest.mark.parametrize(
    ("skill", "script", "domain", "fixture"),
    [
        (
            "test-crypto-interoperability",
            "record_case.py",
            "crypto",
            "interoperability_input",
        ),
        (
            "qualify-entropy-source",
            "qualify_run.py",
            "entropy",
            "qualification_input",
        ),
    ],
)
def test_evidence_helpers_reject_secret_fields(
    skill: str, script: str, domain: str, fixture: str
) -> None:
    payload = _fixture(domain)[fixture]
    payload["private_key"] = "do-not-collect"
    path = ROOT / "core" / "skills" / skill / "scripts" / script
    result = subprocess.run(
        [sys.executable, str(path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "secret or raw key material is forbidden" in result.stderr
    assert "do-not-collect" not in result.stderr


def test_semantic_diff_reports_confidence_and_evidence_hash_changes() -> None:
    data = _fixture("crypto")
    after = json.loads(json.dumps(data["cbom_before"]))
    after["repository"]["revision"] = "confidence-change"
    after["assets"][0]["confidence"] = "low"
    after["assets"][0]["evidence_hash"] = (
        "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    delta = _run(
        "review-crypto-delta",
        "semantic_diff.py",
        {"before": data["cbom_before"], "after": after},
    )

    assert delta["changes"][0]["fields"] == {
        "confidence": {"before": "high", "after": "low"},
        "evidence_hash": {
            "before": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "after": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }


def test_entropy_helpers_emit_schema_valid_qualification_contracts() -> None:
    data = _fixture("entropy")
    cases = [
        (
            "qualify-entropy-source",
            "qualify_run.py",
            data["qualification_input"],
            data["qualification_run_expected"],
            "qualification-run.schema.json",
        ),
        (
            "review-entropy-change",
            "decide_requalification.py",
            {"before": data["prior_source"], "after": data["changed_source"]},
            data["requalification_decision_expected"],
            "requalification-decision.schema.json",
        ),
    ]
    for skill, script, payload, expected, schema_name in cases:
        actual = _run(skill, script, payload)
        assert actual == expected
        schema = json.loads(
            (
                ROOT / "core" / "skills" / skill / "references" / schema_name
            ).read_text()
        )
        _validate(actual, schema)

    source_schema = json.loads(
        (
            ROOT
            / "core/skills/qualify-entropy-source/references/entropy-source.schema.json"
        ).read_text()
    )
    health_schema = json.loads(
        (
            ROOT
            / "core/skills/qualify-entropy-source/references/health-test-parameters.schema.json"
        ).read_text()
    )
    _validate(data["qualification_input"]["source_identity"], source_schema)
    _validate(data["qualification_input"]["health_test_parameters"], health_schema)


def test_entropy_qualification_fails_below_claimed_min_entropy() -> None:
    actual = _run(
        "qualify-entropy-source",
        "qualify_run.py",
        _fixture("entropy")["qualification_input"],
    )
    assert (
        actual["observed_min_entropy_bits_per_sample"]
        < actual["claimed_min_entropy_bits_per_sample"]
    )
    assert actual["evidence_state"] == "fail"


def test_requalification_exceptions_must_be_version_pinned_and_exact() -> None:
    data = _fixture("entropy")
    comparison = {"before": data["prior_source"], "after": data["changed_source"]}
    unpinned = {
        **comparison,
        "exception_policy": {"fields": ["firmware_identity"]},
    }
    exact = {
        **comparison,
        "exception_policy": {
            "revision": "entropy-exceptions@2026-07-09",
            "exceptions": [
                {
                    "field": "firmware_identity",
                    "before": data["prior_source"]["firmware_identity"],
                    "after": data["changed_source"]["firmware_identity"],
                }
            ],
        },
    }

    assert _run(
        "review-entropy-change", "decide_requalification.py", unpinned
    )["decision"] == "requalification-required"
    waived = _run("review-entropy-change", "decide_requalification.py", exact)
    assert waived["decision"] == "review-required"
    assert waived["policy_revision"] == "entropy-exceptions@2026-07-09"


def test_skills_have_portable_metadata_pinned_sources_and_non_claims() -> None:
    for skill, (schema_name, script_name) in SKILLS.items():
        directory = ROOT / "core" / "skills" / skill
        text = (directory / "SKILL.md").read_text()
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        assert frontmatter["name"] == skill
        assert frontmatter["description"]
        assert (directory / "references" / schema_name).is_file()
        assert (directory / "scripts" / script_name).is_file()
        assert "does not certify" in text.lower()
        assert "secret" in text.lower()
        references = (directory / "references" / "authoritative-sources.md").read_text()
        assert "Pinned references" in references
        assert "accessed 2026-07-09" in references

    pqc = (
        ROOT
        / "core/skills/plan-pqc-migration/references/authoritative-sources.md"
    ).read_text()
    for publication in ("FIPS 203", "FIPS 204", "FIPS 205", "NIST.IR.8547"):
        assert publication in pqc
    entropy = (
        ROOT
        / "core/skills/qualify-entropy-source/references/authoritative-sources.md"
    ).read_text()
    assert "NIST.SP.800-90B" in entropy


def test_codex_adapters_have_six_bounded_agents_and_narrow_hooks() -> None:
    expected_agents = {
        "crypto-change-radar": {
            "crypto-archaeologist",
            "protocol-challenger",
            "evidence-notary",
        },
        "entropy-flight-recorder": {
            "entropy-analyst",
            "source-physics-skeptic",
            "evidence-curator",
        },
    }
    for plugin, names in expected_agents.items():
        adapter = ROOT / "adapters" / "codex" / plugin
        manifest = json.loads(
            (adapter / ".codex-plugin" / "plugin.json").read_text()
        )
        assert manifest["interface"]["displayName"]
        agents = {
            path.stem: tomllib.loads(path.read_text())
            for path in (adapter / "agents").glob("*.toml")
        }
        assert set(agents) == names
        for agent in agents.values():
            assert all(agent[key] for key in ("name", "description", "developer_instructions"))
            instructions = " ".join(agent["developer_instructions"].lower().split())
            assert "cannot certify fips status, quantum origin, or entropy adequacy" in instructions
            assert "secret" in instructions

        hooks = json.loads((adapter / "hooks" / "hooks.json").read_text())
        assert set(hooks["hooks"]) == {"PreToolUse", "PostToolUse"}
        for groups in hooks["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    assert hook["timeout"] <= 5
                    assert "${PLUGIN_ROOT}/hooks/scripts/" in hook["command"]

def _assert_objects_are_closed(schema: object, location: str = "$") -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False, location
        for key, value in schema.items():
            _assert_objects_are_closed(value, f"{location}.{key}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            _assert_objects_are_closed(value, f"{location}[{index}]")


def test_all_crypto_entropy_contract_objects_are_closed() -> None:
    references = [
        path
        for skill in SKILLS
        for path in (ROOT / "core" / "skills" / skill / "references").glob(
            "*.schema.json"
        )
    ]
    assert references
    for path in references:
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        _assert_objects_are_closed(schema, path.relative_to(ROOT).as_posix())


@pytest.mark.parametrize(
    "credential_key",
    [
        "access_token",
        "accessToken",
        "client_secret",
        "Authorization",
        "refresh-token",
        "aws_secret_access_key",
    ],
)
def test_recursive_credential_patterns_are_rejected_without_echo(
    credential_key: str,
) -> None:
    payload = _fixture("crypto")["cbom_before"]
    payload["assets"][0]["parameters"]["nested"] = {
        credential_key: "sensitive-value"
    }
    script = ROOT / "core/skills/build-crypto-inventory/scripts/build_inventory.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "credential-bearing field is forbidden" in result.stderr
    assert "sensitive-value" not in result.stderr


def test_production_validator_rejects_undeclared_cbom_properties() -> None:
    payload = _fixture("crypto")["cbom_before"]
    payload["undeclared"] = True
    script = ROOT / "core/skills/build-crypto-inventory/scripts/build_inventory.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "contract validation failed" in result.stderr


def _codex_payload(
    *,
    event: str,
    tool_name: str,
    tool_input: dict[str, Any],
    cwd: Path,
) -> dict[str, Any]:
    payload = {
        "session_id": "019-test-session",
        "turn_id": "turn-7",
        "transcript_path": None,
        "cwd": str(cwd),
        "hook_event_name": event,
        "model": "gpt-5.6-codex",
        "permission_mode": "default",
        "tool_name": tool_name,
        "tool_use_id": "call-22",
        "tool_input": tool_input,
    }
    if event == "PostToolUse":
        payload["tool_response"] = {"ok": True, "exit_code": 0}
    return payload


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _trusted_bwrap_available() -> bool:
    path = Path("/usr/bin/bwrap")
    try:
        metadata = path.stat()
    except OSError:
        return False
    return (
        path.is_file()
        and not path.is_symlink()
        and metadata.st_uid == 0
        and (metadata.st_mode & 0o022) == 0
        and os.access(path, os.X_OK)
    )


def _registration_script(plugin: str) -> Path:
    skill = (
        "check-crypto-runtime"
        if plugin == "crypto-change-radar"
        else "check-entropy-runtime"
    )
    return (
        ROOT
        / "adapters"
        / "codex"
        / plugin
        / "skills"
        / skill
        / "scripts"
        / "register_control_state.py"
    )


def _provision_test_trust(
    root: Path, plugin: str, plugin_data: Path
) -> tuple[Path, dict[str, str]]:
    private_key = root.parent / f"{root.name}-{plugin}-signing-key.pem"
    boundary = root.parent / f"{root.name}-{plugin}-trust-boundary"
    boundary.mkdir(mode=0o700)
    trust_root = boundary / f"{plugin}.pem"
    subprocess.run(
        [
            "/usr/bin/openssl",
            "genpkey",
            "-algorithm",
            "ED25519",
            "-out",
            str(private_key),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "/usr/bin/openssl",
            "pkey",
            "-in",
            str(private_key),
            "-pubout",
            "-out",
            str(trust_root),
        ],
        check=True,
        capture_output=True,
    )
    private_key.chmod(0o600)
    trust_root.chmod(0o444)
    boundary.chmod(0o555)
    trust_variable = (
        "CRYPTO_CHANGE_RADAR_TRUST_ROOT"
        if plugin == "crypto-change-radar"
        else "ENTROPY_FLIGHT_RECORDER_TRUST_ROOT"
    )
    boundary_variable = (
        "CRYPTO_CHANGE_RADAR_TRUST_BOUNDARY"
        if plugin == "crypto-change-radar"
        else "ENTROPY_FLIGHT_RECORDER_TRUST_BOUNDARY"
    )
    uid_variable = (
        "CRYPTO_CHANGE_RADAR_TRUSTED_UID"
        if plugin == "crypto-change-radar"
        else "ENTROPY_FLIGHT_RECORDER_TRUSTED_UID"
    )
    return private_key, {
        "PLUGIN_DATA": str(plugin_data),
        trust_variable: str(trust_root),
        boundary_variable: str(boundary),
        uid_variable: str(os.getuid()),
    }


def _sign_test_payload(
    root: Path,
    plugin: str,
    private_key: Path,
    signing_payload: object,
    label: str = "approval",
) -> Path:
    payload_path = root / f"{plugin}-{label}-payload.json"
    payload_path.write_bytes(
        json.dumps(signing_payload, sort_keys=True, separators=(",", ":")).encode()
    )
    signature = root / f"{plugin}-{label}.sig"
    subprocess.run(
        [
            "/usr/bin/openssl",
            "pkeyutl",
            "-sign",
            "-inkey",
            str(private_key),
            "-rawin",
            "-in",
            str(payload_path),
            "-out",
            str(signature),
        ],
        check=True,
        capture_output=True,
    )
    return signature


def _managed_state(
    root: Path, plugin: str, filename: str, value: object
) -> dict[str, str]:
    plugin_data = root.parent / f"{root.name}-plugin-data"
    state = plugin_data / plugin
    candidate = root / f"candidate-{filename}"
    candidate.write_text(json.dumps(value), encoding="utf-8")
    private_key, control_env = _provision_test_trust(root, plugin, plugin_data)
    script = _registration_script(plugin)
    command = [
        sys.executable,
        str(script),
        "--state-dir",
        str(state),
        "--project-root",
        str(root),
        "--artifact",
        str(candidate),
        "--approver-id",
        "test-approver",
        "--signed-at",
        "2026-07-10T01:00:00Z",
    ]
    prepared = subprocess.run(
        [*command, "--prepare"],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    signing_payload = json.loads(prepared.stdout)["signing_payload"]
    signature = _sign_test_payload(
        root, plugin, private_key, signing_payload
    )
    subprocess.run(
        [*command, "--signature", str(signature)],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    return control_env


def _write_crypto_policy(root: Path) -> dict[str, str]:
    policy = {
        "policy_version": "crypto-policy@2026-07-10",
        "forbidden_primitives": ["MD5", "RC4"],
    }
    return _managed_state(root, "crypto-change-radar", "crypto-policy.json", policy)


def _write_entropy_baseline(
    root: Path, source: dict[str, Any]
) -> dict[str, str]:
    baseline = {
        "baseline_version": "entropy-baseline@2026-07-10",
        "source_identity": source,
        "source_identity_hash": _canonical_hash(source),
    }
    return _managed_state(
        root,
        "entropy-flight-recorder",
        "entropy-baseline.json",
        baseline,
    )


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("Write", {"file_path": "evidence/cbom.json", "content": "{}"}),
        (
            "Edit",
            {
                "file_path": "evidence/cbom.json",
                "old_string": "{}",
                "new_string": "{\"schema_version\":\"1.0\"}",
            },
        ),
        (
            "apply_patch",
            {
                "command": (
                    "*** Begin Patch\n"
                    "*** Update File: evidence/cbom.json\n"
                    "@@\n-{}\n+{}\n"
                    "*** End Patch\n"
                )
            },
        ),
        ("Bash", {"command": "python3 collect.py > evidence/cbom.json"}),
    ],
)
def test_crypto_hook_parses_authentic_codex_payloads_and_validates_files(
    tmp_path: Path,
    tool_name: str,
    tool_input: dict[str, Any],
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control_env = _write_crypto_policy(tmp_path)
    (evidence / "cbom.json").write_text(
        json.dumps(_fixture("crypto")["cbom_before"]), encoding="utf-8"
    )
    script = (
        ROOT
        / "adapters/codex/crypto-change-radar/hooks/scripts/check_crypto_inputs.py"
    )
    pre = subprocess.run(
        [
            sys.executable,
            str(script),
        ],
        input=json.dumps(
            _codex_payload(
                event="PreToolUse",
                tool_name=tool_name,
                tool_input=tool_input,
                cwd=tmp_path,
            )
        ),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    post = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(
            _codex_payload(
                event="PostToolUse",
                tool_name=tool_name,
                tool_input=tool_input,
                cwd=tmp_path,
            )
        ),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )

    pre_output = json.loads(pre.stdout)["hookSpecificOutput"]
    post_output = json.loads(post.stdout)["hookSpecificOutput"]
    assert pre_output["hookEventName"] == "PreToolUse"
    assert "evidence/cbom.json" in pre_output["additionalContext"]
    assert post_output["hookEventName"] == "PostToolUse"
    assert "evidence-state=pass" in post_output["additionalContext"]
    assert "evidence/cbom.json" in post_output["additionalContext"]


def test_crypto_hook_blocks_policy_forbidden_primitive(tmp_path: Path) -> None:
    control_env = _write_crypto_policy(tmp_path)
    artifact = _fixture("crypto")["cbom_before"]
    artifact["assets"][0]["algorithm"] = "MD5"
    (tmp_path / "cbom.json").write_text(json.dumps(artifact), encoding="utf-8")
    script = (
        ROOT
        / "adapters/codex/crypto-change-radar/hooks/scripts/check_crypto_inputs.py"
    )
    payload = _codex_payload(
        event="PostToolUse",
        tool_name="apply_patch",
        tool_input={"command": "*** Update File: cbom.json\n@@\n"},
        cwd=tmp_path,
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert "MD5" in output["reason"]
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "evidence-state=fail" in output["hookSpecificOutput"]["additionalContext"]


def test_entropy_hook_reports_invalid_result_from_authentic_post_payload(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "qualification-run.json"
    source = _fixture("entropy")["qualification_input"]["source_identity"]
    control_env = _write_entropy_baseline(tmp_path, source)
    invalid = _fixture("entropy")["qualification_run_expected"]
    invalid["undeclared"] = True
    artifact.write_text(json.dumps(invalid), encoding="utf-8")
    script = (
        ROOT
        / "adapters/codex/entropy-flight-recorder/hooks/scripts/check_entropy_inputs.py"
    )
    payload = _codex_payload(
        event="PostToolUse",
        tool_name="apply_patch",
        tool_input={
            "command": (
                "*** Begin Patch\n"
                "*** Update File: qualification-run.json\n"
                "@@\n-{}\n+{}\n"
                "*** End Patch\n"
            )
        },
        cwd=tmp_path,
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PostToolUse"
    assert "evidence-state=fail" in output["additionalContext"]
    assert "qualification-run.json" in output["additionalContext"]


def test_entropy_hook_blocks_source_boundary_change(tmp_path: Path) -> None:
    source = _fixture("entropy")["qualification_input"]["source_identity"]
    control_env = _write_entropy_baseline(tmp_path, source)
    changed = json.loads(json.dumps(source))
    changed["firmware_identity"] = "fw-unsafe"
    (tmp_path / "entropy-source.json").write_text(
        json.dumps(changed), encoding="utf-8"
    )
    script = (
        ROOT
        / "adapters/codex/entropy-flight-recorder/hooks/scripts/check_entropy_inputs.py"
    )
    payload = _codex_payload(
        event="PostToolUse",
        tool_name="Write",
        tool_input={"file_path": "entropy-source.json", "content": "{}"},
        cwd=tmp_path,
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert "firmware_identity" in output["reason"]
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"


@pytest.mark.parametrize(
    ("plugin", "script_name", "protected_name", "artifact_name", "fixture_domain", "fixture_name"),
    [
        (
            "crypto-change-radar",
            "check_crypto_inputs.py",
            "crypto-policy.json",
            "cbom.json",
            "crypto",
            "cbom_before",
        ),
        (
            "entropy-flight-recorder",
            "check_entropy_inputs.py",
            "entropy-baseline.json",
            "qualification-run.json",
            "entropy",
            "qualification_run_expected",
        ),
    ],
)
def test_hooks_block_one_patch_policy_weakening_plus_artifact_change(
    tmp_path: Path,
    plugin: str,
    script_name: str,
    protected_name: str,
    artifact_name: str,
    fixture_domain: str,
    fixture_name: str,
) -> None:
    if plugin == "crypto-change-radar":
        control_env = _write_crypto_policy(tmp_path)
    else:
        control_env = _write_entropy_baseline(
            tmp_path, _fixture("entropy")["qualification_input"]["source_identity"]
        )
    (tmp_path / artifact_name).write_text(
        json.dumps(_fixture(fixture_domain)[fixture_name]), encoding="utf-8"
    )
    script = ROOT / "adapters" / "codex" / plugin / "hooks" / "scripts" / script_name
    patch = (
        "*** Begin Patch\n"
        f"*** Update File: {protected_name}\n@@\n-{{}}\n+{{\"approved\":true}}\n"
        f"*** Update File: {artifact_name}\n@@\n-{{}}\n+{{}}\n"
        "*** End Patch\n"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(
            _codex_payload(
                event="PostToolUse",
                tool_name="apply_patch",
                tool_input={"command": patch},
                cwd=tmp_path,
            )
        ),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert output["hookSpecificOutput"]["decision"] == "block"
    assert protected_name in output["reason"]
    assert "external control-plane" in output["reason"]


@pytest.mark.parametrize(
    ("plugin", "skill_name", "artifact_name", "artifact"),
    [
        (
            "crypto-change-radar",
            "check-crypto-runtime",
            "crypto-policy.json",
            {
                "policy_version": "crypto-policy@2026-07-10",
                "forbidden_primitives": ["MD5"],
            },
        ),
        (
            "entropy-flight-recorder",
            "check-entropy-runtime",
            "entropy-baseline.json",
            {
                "baseline_version": "entropy-baseline@2026-07-10",
                "source_identity": _fixture("entropy")["qualification_input"][
                    "source_identity"
                ],
                "source_identity_hash": _canonical_hash(
                    _fixture("entropy")["qualification_input"]["source_identity"]
                ),
            },
        ),
    ],
)
def test_control_state_registration_requires_detached_signed_approval(
    tmp_path: Path,
    plugin: str,
    skill_name: str,
    artifact_name: str,
    artifact: dict[str, Any],
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    candidate = tmp_path / f"candidate-{artifact_name}"
    candidate.write_text(json.dumps(artifact), encoding="utf-8")
    plugin_data = tmp_path / "plugin-data"
    state = plugin_data / plugin
    script = _registration_script(plugin)
    private_key, control_env = _provision_test_trust(
        tmp_path, plugin, plugin_data
    )
    command = [
        sys.executable,
        str(script),
        "--state-dir",
        str(state),
        "--project-root",
        str(project),
        "--artifact",
        str(candidate),
        "--approver-id",
        "human:test",
        "--signed-at",
        "2026-07-10T01:00:00Z",
    ]
    refused = subprocess.run(
        [*command, "--approve"],
        text=True,
        capture_output=True,
        env={**os.environ, **control_env},
    )
    assert refused.returncode == 2
    assert "--prepare --signature is required" in refused.stderr
    assert not state.exists()
    prepared = subprocess.run(
        [*command, "--prepare"],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    signing_payload = json.loads(prepared.stdout)["signing_payload"]
    signature = _sign_test_payload(
        tmp_path, plugin, private_key, signing_payload, "first"
    )
    attacker_command = [
        value if value != "human:test" else "attacker:self"
        for value in command
    ]
    attacker = subprocess.run(
        [*attacker_command, "--signature", str(signature)],
        text=True,
        capture_output=True,
        env={**os.environ, **control_env},
    )
    assert attacker.returncode == 3
    assert json.loads(attacker.stdout)["evidence_state"] == "evidence-gap"
    assert not state.exists()
    approved = subprocess.run(
        [*command, "--signature", str(signature)],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    result = json.loads(approved.stdout)
    assert result["authority"] == "detached-signature-with-local-hmac-chain"
    assert (state / artifact_name).is_file()
    assert (state / "control-state.key").stat().st_mode & 0o777 == 0o600
    assert (state / "control-state.lock").stat().st_mode & 0o777 == 0o600
    assert (state / "approval-ledger.jsonl").stat().st_mode & 0o777 == 0o600
    first = json.loads((state / "approval-ledger.jsonl").read_text().splitlines()[0])
    signed = first["signed_payload"]
    assert signed["artifact_digest"] == result["digest"]
    assert signed["decision"] == "approve"
    assert signed["approver_id"] == "human:test"
    assert signed["plugin"] == plugin
    assert signed["signed_at"] == "2026-07-10T01:00:00Z"
    assert signed["prior_entry_hash"] == "sha256:" + ("0" * 64)
    second_command = [
        value if value != "human:test" else "human:second" for value in command
    ]
    second_command = [
        value if value != "2026-07-10T01:00:00Z" else "2026-07-10T02:00:00Z"
        for value in second_command
    ]
    second_prepared = subprocess.run(
        [*second_command, "--prepare"],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    second_payload = json.loads(second_prepared.stdout)["signing_payload"]
    second_signature = _sign_test_payload(
        tmp_path, plugin, private_key, second_payload, "second"
    )
    second = subprocess.run(
        [*second_command, "--signature", str(second_signature)],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    assert json.loads(second.stdout)["sequence"] == 2
    entries = [
        json.loads(line)
        for line in (state / "approval-ledger.jsonl").read_text().splitlines()
    ]
    assert entries[1]["prior_entry_hmac"] == entries[0]["entry_hmac"]
    assert entries[1]["signed_payload"]["approver_id"] == "human:second"
    assert entries[1]["signed_payload"]["prior_entry_hash"] == _canonical_hash(
        entries[0]
    )


@pytest.mark.parametrize("trust_failure", ["missing", "writable"])
def test_registration_refuses_missing_or_writable_trust_root(
    tmp_path: Path, trust_failure: str
) -> None:
    plugin = "crypto-change-radar"
    plugin_data = tmp_path / "plugin-data"
    state = plugin_data / plugin
    project = tmp_path / "project"
    project.mkdir()
    candidate = tmp_path / "candidate-policy.json"
    candidate.write_text(
        json.dumps(
            {
                "policy_version": "crypto-policy@2026-07-10",
                "forbidden_primitives": ["MD5"],
            }
        ),
        encoding="utf-8",
    )
    if trust_failure == "writable":
        _, control_env = _provision_test_trust(tmp_path, plugin, plugin_data)
        trust_root = Path(control_env["CRYPTO_CHANGE_RADAR_TRUST_ROOT"])
        trust_root.chmod(0o644)
    else:
        control_env = {"PLUGIN_DATA": str(plugin_data)}
    result = subprocess.run(
        [
            sys.executable,
            str(_registration_script(plugin)),
            "--state-dir",
            str(state),
            "--project-root",
            str(project),
            "--artifact",
            str(candidate),
            "--approver-id",
            "human:test",
            "--signed-at",
            "2026-07-10T01:00:00Z",
            "--prepare",
        ],
        text=True,
        capture_output=True,
        env={**os.environ, **control_env},
    )
    assert result.returncode == 3
    refusal = json.loads(result.stdout)
    assert refusal["evidence_state"] == "evidence-gap"
    assert "trust" in refusal["guidance"]
    assert not state.exists()


@pytest.mark.parametrize("plugin", ["crypto-change-radar", "entropy-flight-recorder"])
@pytest.mark.parametrize(
    "boundary_failure",
    ["replaceable", "writable-parent", "wrong-owner", "symlink"],
)
def test_registration_rejects_untrusted_public_key_path_components(
    tmp_path: Path, plugin: str, boundary_failure: str
) -> None:
    plugin_data = tmp_path / "plugin-data"
    state = plugin_data / plugin
    project = tmp_path / "project"
    project.mkdir()
    if plugin == "crypto-change-radar":
        artifact = {
            "policy_version": "crypto-policy@2026-07-10",
            "forbidden_primitives": ["MD5"],
        }
        artifact_name = "crypto-policy.json"
        boundary_variable = "CRYPTO_CHANGE_RADAR_TRUST_BOUNDARY"
        root_variable = "CRYPTO_CHANGE_RADAR_TRUST_ROOT"
        uid_variable = "CRYPTO_CHANGE_RADAR_TRUSTED_UID"
    else:
        source = _fixture("entropy")["qualification_input"]["source_identity"]
        artifact = {
            "baseline_version": "entropy-baseline@2026-07-10",
            "source_identity": source,
            "source_identity_hash": _canonical_hash(source),
        }
        artifact_name = "entropy-baseline.json"
        boundary_variable = "ENTROPY_FLIGHT_RECORDER_TRUST_BOUNDARY"
        root_variable = "ENTROPY_FLIGHT_RECORDER_TRUST_ROOT"
        uid_variable = "ENTROPY_FLIGHT_RECORDER_TRUSTED_UID"
    candidate = tmp_path / f"candidate-{artifact_name}"
    candidate.write_text(json.dumps(artifact), encoding="utf-8")
    _, control_env = _provision_test_trust(tmp_path, plugin, plugin_data)
    boundary = Path(control_env[boundary_variable])
    trust = Path(control_env[root_variable])
    if boundary_failure == "replaceable":
        boundary.chmod(0o755)
        _, replacement_env = _provision_test_trust(
            tmp_path / "replacement", plugin, plugin_data
        )
        replacement = Path(replacement_env[root_variable]).read_bytes()
        trust.unlink()
        trust.write_bytes(replacement)
        trust.chmod(0o444)
    elif boundary_failure == "writable-parent":
        boundary.chmod(0o755)
        nested = boundary / "group-writable"
        nested.mkdir(mode=0o775)
        moved = nested / trust.name
        trust.rename(moved)
        nested.chmod(0o775)
        boundary.chmod(0o555)
        control_env[root_variable] = str(moved)
    elif boundary_failure == "wrong-owner":
        control_env[uid_variable] = str(os.getuid() + 1)
    else:
        boundary.chmod(0o755)
        real_parent = boundary / "real"
        real_parent.mkdir(mode=0o700)
        moved = real_parent / trust.name
        trust.rename(moved)
        real_parent.chmod(0o555)
        linked_parent = boundary / "linked"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        boundary.chmod(0o555)
        control_env[root_variable] = str(linked_parent / trust.name)
    result = subprocess.run(
        [
            sys.executable,
            str(_registration_script(plugin)),
            "--state-dir",
            str(state),
            "--project-root",
            str(project),
            "--artifact",
            str(candidate),
            "--approver-id",
            "human:test",
            "--signed-at",
            "2026-07-10T01:00:00Z",
            "--prepare",
        ],
        text=True,
        capture_output=True,
        env={**os.environ, **control_env},
    )
    assert result.returncode == 3
    refusal = json.loads(result.stdout)
    assert refusal["evidence_state"] == "evidence-gap"
    assert "trust" in refusal["guidance"]
    assert not state.exists()


def test_crypto_hook_rejects_approved_self_hash_without_managed_digest(
    tmp_path: Path,
) -> None:
    plugin_data = tmp_path.parent / f"{tmp_path.name}-untrusted-plugin-data"
    state = plugin_data / "crypto-change-radar"
    state.mkdir(parents=True)
    policy = {
        "policy_version": "crypto-policy@2026-07-10",
        "approved": True,
        "forbidden_primitives": [],
    }
    policy["policy_hash"] = _canonical_hash(policy)
    (state / "crypto-policy.json").write_text(json.dumps(policy), encoding="utf-8")
    (tmp_path / "cbom.json").write_text(
        json.dumps(_fixture("crypto")["cbom_before"]), encoding="utf-8"
    )
    script = (
        ROOT
        / "adapters/codex/crypto-change-radar/hooks/scripts/check_crypto_inputs.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(
            _codex_payload(
                event="PostToolUse",
                tool_name="Write",
                tool_input={"file_path": "cbom.json", "content": "{}"},
                cwd=tmp_path,
            )
        ),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, "PLUGIN_DATA": str(plugin_data)},
    )
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert output["hookSpecificOutput"]["decision"] == "block"
    assert "evidence-gap: explicit managed trust boundary is missing" in output["reason"]


def test_entropy_hook_rejects_approved_self_hash_without_managed_digest(
    tmp_path: Path,
) -> None:
    plugin_data = tmp_path.parent / f"{tmp_path.name}-untrusted-plugin-data"
    state = plugin_data / "entropy-flight-recorder"
    state.mkdir(parents=True)
    source = _fixture("entropy")["qualification_input"]["source_identity"]
    baseline = {
        "baseline_version": "entropy-baseline@2026-07-10",
        "approved": True,
        "source_identity": source,
        "source_identity_hash": _canonical_hash(source),
    }
    (state / "entropy-baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )
    (tmp_path / "qualification-run.json").write_text(
        json.dumps(_fixture("entropy")["qualification_run_expected"]),
        encoding="utf-8",
    )
    script = (
        ROOT
        / "adapters/codex/entropy-flight-recorder/hooks/scripts/check_entropy_inputs.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(
            _codex_payload(
                event="PostToolUse",
                tool_name="Write",
                tool_input={"file_path": "qualification-run.json", "content": "{}"},
                cwd=tmp_path,
            )
        ),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, "PLUGIN_DATA": str(plugin_data)},
    )
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert output["hookSpecificOutput"]["decision"] == "block"
    assert "evidence-gap: explicit managed trust boundary is missing" in output["reason"]


@pytest.mark.parametrize(
    ("plugin", "script_name", "artifact_name", "fixture_domain", "fixture_name"),
    [
        (
            "crypto-change-radar",
            "check_crypto_inputs.py",
            "cbom.json",
            "crypto",
            "cbom_before",
        ),
        (
            "entropy-flight-recorder",
            "check_entropy_inputs.py",
            "qualification-run.json",
            "entropy",
            "qualification_run_expected",
        ),
    ],
)
@pytest.mark.parametrize(
    "tamper_kind",
    [
        "policy-rewrite",
        "ledger-rewrite",
        "key-mismatch",
        "trust-root-mismatch",
        "missing-state",
    ],
)
def test_hooks_block_tampered_or_missing_authenticated_control_state(
    tmp_path: Path,
    plugin: str,
    script_name: str,
    artifact_name: str,
    fixture_domain: str,
    fixture_name: str,
    tamper_kind: str,
) -> None:
    if plugin == "crypto-change-radar":
        control_env = _write_crypto_policy(tmp_path)
        control_name = "crypto-policy.json"
    else:
        control_env = _write_entropy_baseline(
            tmp_path, _fixture("entropy")["qualification_input"]["source_identity"]
        )
        control_name = "entropy-baseline.json"
    state = Path(control_env["PLUGIN_DATA"]) / plugin
    if tamper_kind == "policy-rewrite":
        control = json.loads((state / control_name).read_text())
        version_field = (
            "policy_version"
            if plugin == "crypto-change-radar"
            else "baseline_version"
        )
        control[version_field] = control[version_field].replace(
            "2026-07-10", "2026-07-11"
        )
        (state / control_name).write_text(json.dumps(control), encoding="utf-8")
    elif tamper_kind == "ledger-rewrite":
        ledger = state / "approval-ledger.jsonl"
        entry = json.loads(ledger.read_text().splitlines()[0])
        entry["signed_payload"]["approver_id"] = "attacker:self"
        ledger.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    elif tamper_kind == "key-mismatch":
        (state / "control-state.key").write_bytes(b"x" * 32)
    elif tamper_kind == "trust-root-mismatch":
        _, wrong_env = _provision_test_trust(
            tmp_path / "wrong-root", plugin, Path(control_env["PLUGIN_DATA"])
        )
        control_env.update(wrong_env)
    else:
        (state / "approval-ledger.jsonl").unlink()
    (tmp_path / artifact_name).write_text(
        json.dumps(_fixture(fixture_domain)[fixture_name]), encoding="utf-8"
    )
    script = ROOT / "adapters" / "codex" / plugin / "hooks" / "scripts" / script_name
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(
            _codex_payload(
                event="PostToolUse",
                tool_name="Write",
                tool_input={"file_path": artifact_name, "content": "{}"},
                cwd=tmp_path,
            )
        ),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert output["hookSpecificOutput"]["decision"] == "block"
    assert "authenticated" in output["reason"]


@pytest.mark.parametrize(
    ("plugin", "script_name", "artifact_name", "domain", "fixture_name"),
    [
        (
            "crypto-change-radar",
            "check_crypto_inputs.py",
            "cbom.json",
            "crypto",
            "cbom_before",
        ),
        (
            "entropy-flight-recorder",
            "check_entropy_inputs.py",
            "qualification-run.json",
            "entropy",
            "qualification_run_expected",
        ),
    ],
)
def test_hooks_report_validator_unavailable_with_setup_guidance(
    tmp_path: Path,
    plugin: str,
    script_name: str,
    artifact_name: str,
    domain: str,
    fixture_name: str,
) -> None:
    if plugin == "crypto-change-radar":
        control_env = _write_crypto_policy(tmp_path)
    else:
        control_env = _write_entropy_baseline(
            tmp_path, _fixture("entropy")["qualification_input"]["source_identity"]
        )
    (tmp_path / artifact_name).write_text(
        json.dumps(_fixture(domain)[fixture_name]), encoding="utf-8"
    )
    script = ROOT / "adapters" / "codex" / plugin / "hooks" / "scripts" / script_name
    payload = _codex_payload(
        event="PostToolUse",
        tool_name="Write",
        tool_input={"file_path": artifact_name, "content": "{}"},
        cwd=tmp_path,
    )
    result = subprocess.run(
        [sys.executable, "-S", str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, **control_env},
    )
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert "evidence-state=evidence-gap" in output["additionalContext"]
    assert "check-" in output["additionalContext"]
    assert "runtime" in output["additionalContext"]


@pytest.mark.parametrize(
    ("plugin", "skill_name"),
    [
        ("crypto-change-radar", "check-crypto-runtime"),
        ("entropy-flight-recorder", "check-entropy-runtime"),
    ],
)
def test_runtime_check_skills_are_idempotent_and_never_install(
    plugin: str, skill_name: str
) -> None:
    directory = ROOT / "adapters" / "codex" / plugin / "skills" / skill_name
    text = (directory / "SKILL.md").read_text()
    assert "does not install" in text.lower()
    script = directory / "scripts" / "check_runtime.py"
    first = subprocess.run(
        [sys.executable, str(script)], text=True, capture_output=True, check=True
    )
    second = subprocess.run(
        [sys.executable, str(script)], text=True, capture_output=True, check=True
    )
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["evidence_state"] == "pass"
    unavailable = subprocess.run(
        [sys.executable, "-S", str(script)],
        text=True,
        capture_output=True,
    )
    assert unavailable.returncode == 3
    payload = json.loads(unavailable.stdout)
    assert payload["evidence_state"] == "evidence-gap"
    assert "pip install jsonschema==4.26.0" in payload["setup_guidance"]


def test_standalone_helper_reports_missing_validator_as_evidence_gap() -> None:
    script = ROOT / "core/skills/build-crypto-inventory/scripts/build_inventory.py"
    result = subprocess.run(
        [sys.executable, "-S", str(script)],
        input=json.dumps(_fixture("crypto")["cbom_before"]),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 3
    assert "evidence-gap" in result.stderr
    assert "check-crypto-runtime" in result.stderr


def test_collector_is_deterministic_and_marks_unavailable_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text(
        "import hashlib\nhashlib.sha256(b'test').digest()\n", encoding="utf-8"
    )
    (tmp_path / "package-lock.json").write_text(
        '{"dependencies":{"openssl-wrapper":{"version":"1.0"}}}\n',
        encoding="utf-8",
    )
    (tmp_path / "service.bin").write_bytes(b"\x00AES-256-GCM\x00")
    (tmp_path / "openssl.cnf").write_text("CipherString = RC4\n", encoding="utf-8")
    (tmp_path / "service.crt").write_text(
        "-----BEGIN CERTIFICATE-----\npublic-metadata-only\n"
        "-----END CERTIFICATE-----\n",
        encoding="utf-8",
    )
    payload = {
        "root": str(tmp_path),
        "requests": [
            {"source_class": "binary", "path": "service.bin"},
            {"source_class": "certificate", "path": "service.crt"},
            {"source_class": "source", "path": "src/main.py"},
            {"source_class": "dependency", "path": "package-lock.json"},
            {"source_class": "configuration", "path": "openssl.cnf"},
            {"source_class": "configuration", "path": "missing/openssl.cnf"},
        ],
    }
    first = _run(
        "build-crypto-inventory",
        "collect_evidence.py",
        payload,
    )
    second = _run(
        "build-crypto-inventory",
        "collect_evidence.py",
        payload,
    )
    assert first == second
    assert [item["source_class"] for item in first["asset_candidates"]] == [
        "binary",
        "certificate",
        "configuration",
        "configuration",
        "dependency",
        "source",
    ]
    states = {
        (item["source_class"], item["location"]): item["evidence_state"]
        for item in first["asset_candidates"]
    }
    assert states[("source", "src/main.py")] == "pass"
    assert states[("dependency", "package-lock.json")] == "pass"
    assert states[("binary", "service.bin")] == "pass"
    assert states[("certificate", "service.crt")] == "pass"
    assert states[("configuration", "missing/openssl.cnf")] == "evidence-gap"
    algorithms = {
        (item["source_class"], item["location"]): item["algorithm"]
        for item in first["asset_candidates"]
    }
    assert algorithms[("source", "src/main.py")] == "SHA-256"
    assert algorithms[("binary", "service.bin")] == "AES-256-GCM"
    assert algorithms[("configuration", "openssl.cnf")] == "RC4"


@pytest.mark.parametrize("link_kind", ["root", "ancestor", "leaf"])
def test_collector_rejects_every_symlink_component(
    tmp_path: Path, link_kind: str
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "nested").mkdir()
    (real / "nested/evidence.json").write_text("{}\n", encoding="utf-8")
    if link_kind == "root":
        root = tmp_path / "root-link"
        root.symlink_to(real, target_is_directory=True)
        relative = "nested/evidence.json"
    elif link_kind == "ancestor":
        root = tmp_path
        (root / "linked").symlink_to(real / "nested", target_is_directory=True)
        relative = "linked/evidence.json"
    else:
        root = tmp_path
        (root / "evidence-link.json").symlink_to(real / "nested/evidence.json")
        relative = "evidence-link.json"
    script = (
        ROOT / "core/skills/build-crypto-inventory/scripts/collect_evidence.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(
            {
                "root": str(root),
                "requests": [{"source_class": "dependency", "path": relative}],
            }
        ),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "symlink component is forbidden" in result.stderr


def test_collector_refuses_sensitive_paths_without_hashing_content(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("ACCESS_TOKEN=sensitive-value\n", encoding="utf-8")
    script = (
        ROOT / "core/skills/build-crypto-inventory/scripts/collect_evidence.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(
            {
                "root": str(tmp_path),
                "requests": [{"source_class": "configuration", "path": ".env"}],
            }
        ),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "sensitive evidence path is forbidden" in result.stderr
    assert "sensitive-value" not in result.stderr


def test_interoperability_runner_requires_full_bubblewrap_isolation() -> None:
    data = _fixture("crypto")
    probe = {"negotiated_result": "ML-KEM-768"}
    executable = Path(sys.executable).resolve()
    payload = {
        "case": data["interoperability_input"],
        "runner": {
            "argv": [
                str(executable),
                "-c",
                f"import json; print(json.dumps({probe!r}))",
            ],
            "timeout_seconds": 5,
            "policy": {
                "executable": str(executable),
                "executable_sha256": (
                    f"sha256:{hashlib.sha256(executable.read_bytes()).hexdigest()}"
                ),
                "workdir_policy": "isolated-temporary-directory",
                "sandbox_profile": "bubblewrap-full-isolation",
                "approved_inputs": [],
            },
        },
    }
    actual = _run(
        "test-crypto-interoperability",
        "run_case.py",
        payload,
    )
    assert actual["runner"]["argv"] == payload["runner"]["argv"]
    assert actual["execution"]["sandbox_profile"] == "bubblewrap-full-isolation"
    if not _trusted_bwrap_available():
        assert actual["execution"]["evidence_state"] == "evidence-gap"
        assert actual["execution"]["exit_code"] is None
        assert "bubblewrap" in actual["execution"]["guidance"]
    else:
        assert actual["execution"]["evidence_state"] == "pass"
        assert actual["execution"]["exit_code"] == 0
        expected_case = json.loads(json.dumps(data["interoperability_input"]))
        expected_case.update(probe)
        expected_record = _run(
            "test-crypto-interoperability",
            "record_case.py",
            expected_case,
        )
        assert actual["case_record"]["record_hash"] == expected_record["record_hash"]
    schema = json.loads(
        (
            ROOT
            / "core/skills/test-crypto-interoperability/references/interoperability-run.schema.json"
        ).read_text()
    )
    _validate(actual, schema)


def test_interoperability_runner_refuses_unrestricted_host_command(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "must-not-exist"
    data = _fixture("crypto")
    payload = {
        "case": data["interoperability_input"],
        "runner": {
            "argv": [
                str(Path(sys.executable).resolve()),
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
            ],
            "timeout_seconds": 5,
        },
    }
    actual = _run(
        "test-crypto-interoperability",
        "run_case.py",
        payload,
    )
    assert actual["execution"]["evidence_state"] == "evidence-gap"
    assert not marker.exists()
    assert "safe sandbox policy" in actual["execution"]["guidance"]


def test_interoperability_runner_never_falls_back_to_unshare(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "unshare-fallback-must-not-run"
    executable = Path(sys.executable).resolve()
    payload = {
        "case": _fixture("crypto")["interoperability_input"],
        "runner": {
            "argv": [
                str(executable),
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
            ],
            "timeout_seconds": 5,
            "policy": {
                "executable": str(executable),
                "executable_sha256": (
                    f"sha256:{hashlib.sha256(executable.read_bytes()).hexdigest()}"
                ),
                "workdir_policy": "isolated-temporary-directory",
                "sandbox_profile": "linux-user-network-namespace",
                "approved_inputs": [],
            },
        },
    }
    actual = _run("test-crypto-interoperability", "run_case.py", payload)
    assert actual["execution"]["evidence_state"] == "evidence-gap"
    assert "bubblewrap" in actual["execution"]["guidance"]
    assert not marker.exists()


def test_interoperability_runner_ignores_path_injected_bwrap(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "fake-bwrap-ran"
    fake_bwrap = fake_bin / "bwrap"
    fake_bwrap.write_text(
        (
            "#!/usr/bin/python3\n"
            "from pathlib import Path\n"
            "import json\n"
            f"Path({str(marker)!r}).write_text('ran')\n"
            "print(json.dumps({'negotiated_result':'forged'}))\n"
        ),
        encoding="utf-8",
    )
    fake_bwrap.chmod(0o755)
    executable = Path(sys.executable).resolve()
    payload = {
        "case": _fixture("crypto")["interoperability_input"],
        "runner": {
            "argv": [str(executable), "-c", "print('{}')"],
            "timeout_seconds": 5,
            "policy": {
                "executable": str(executable),
                "executable_sha256": (
                    f"sha256:{hashlib.sha256(executable.read_bytes()).hexdigest()}"
                ),
                "workdir_policy": "isolated-temporary-directory",
                "sandbox_profile": "bubblewrap-full-isolation",
                "approved_inputs": [],
            },
        },
    }
    script = ROOT / "core/skills/test-crypto-interoperability/scripts/run_case.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, "PATH": str(fake_bin)},
    )
    actual = json.loads(result.stdout)
    assert actual["execution"]["evidence_state"] == "evidence-gap"
    assert not marker.exists()


def test_interoperability_command_exposes_no_host_root_or_sensitive_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = (
        ROOT / "core/skills/test-crypto-interoperability/scripts/run_case.py"
    )
    sys.path.insert(0, str(script.parent))
    try:
        spec = importlib.util.spec_from_file_location("isolated_run_case", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    monkeypatch.setattr(
        module, "_trusted_bwrap", lambda: Path("/usr/bin/bwrap")
    )
    executable = Path(sys.executable).resolve()
    output = tmp_path / "output"
    output.mkdir()
    command, refusal = module._safe_command(
        [str(executable), "-c", "print('{}')"],
        {
            "executable": str(executable),
            "executable_sha256": (
                f"sha256:{hashlib.sha256(executable.read_bytes()).hexdigest()}"
            ),
            "workdir_policy": "isolated-temporary-directory",
            "sandbox_profile": "bubblewrap-full-isolation",
            "approved_inputs": [],
        },
        output,
    )
    assert refusal is None
    assert command is not None
    triples = list(zip(command, command[1:], command[2:]))
    assert ("--ro-bind", "/", "/") not in triples
    assert ("--tmpfs", "/", "--dir") in triples
    for forbidden in ("/home", "/workspace", "/etc", str(ROOT)):
        assert forbidden not in command


def test_interoperability_undeclared_host_read_fails() -> None:
    executable = Path(sys.executable).resolve()
    payload = {
        "case": _fixture("crypto")["interoperability_input"],
        "runner": {
            "argv": [
                str(executable),
                "-c",
                (
                    "import json; open('/etc/passwd').read(); "
                    "print(json.dumps({'negotiated_result':'host-read'}))"
                ),
            ],
            "timeout_seconds": 5,
            "policy": {
                "executable": str(executable),
                "executable_sha256": (
                    f"sha256:{hashlib.sha256(executable.read_bytes()).hexdigest()}"
                ),
                "workdir_policy": "isolated-temporary-directory",
                "sandbox_profile": "bubblewrap-full-isolation",
                "approved_inputs": [],
            },
        },
    }
    actual = _run("test-crypto-interoperability", "run_case.py", payload)
    if not _trusted_bwrap_available():
        assert actual["execution"]["evidence_state"] == "evidence-gap"
    else:
        assert actual["execution"]["evidence_state"] == "fail"


def test_interoperability_bubblewrap_prevents_host_write(tmp_path: Path) -> None:
    marker = tmp_path / "host-write-must-not-exist"
    executable = Path(sys.executable).resolve()
    payload = {
        "case": _fixture("crypto")["interoperability_input"],
        "runner": {
            "argv": [
                str(executable),
                "-c",
                (
                    "from pathlib import Path; import json; "
                    f"Path({str(marker)!r}).write_text('escaped'); "
                    "print(json.dumps({'negotiated_result':'isolated'}))"
                ),
            ],
            "timeout_seconds": 5,
            "policy": {
                "executable": str(executable),
                "executable_sha256": (
                    f"sha256:{hashlib.sha256(executable.read_bytes()).hexdigest()}"
                ),
                "workdir_policy": "isolated-temporary-directory",
                "sandbox_profile": "bubblewrap-full-isolation",
                "approved_inputs": [],
            },
        },
    }
    actual = _run("test-crypto-interoperability", "run_case.py", payload)
    assert not marker.exists()
    assert actual["execution"]["evidence_state"] in {"pass", "fail", "evidence-gap"}
    if not _trusted_bwrap_available():
        assert "bubblewrap" in actual["execution"]["guidance"]


def test_invocation_provenance_rejects_credential_flags_without_echo() -> None:
    payload = _fixture("entropy")["qualification_input"]
    payload["estimator_invocations"][0]["argv"].append(
        "--access-token=sensitive-value"
    )
    script = ROOT / "core/skills/qualify-entropy-source/scripts/qualify_run.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "credential-bearing argument is forbidden" in result.stderr
    assert "sensitive-value" not in result.stderr


@pytest.mark.parametrize(
    "parameters",
    [
        {
            "alpha": 0,
            "alphabet_size": 2,
            "claimed_min_entropy_bits_per_sample": 0.73,
        },
        {
            "alpha": 1,
            "alphabet_size": 2,
            "claimed_min_entropy_bits_per_sample": 0.73,
        },
        {
            "alpha": 0.000001,
            "alphabet_size": 2,
            "claimed_min_entropy_bits_per_sample": 1.1,
        },
        {
            "alpha": 0.000001,
            "alphabet_size": 2,
            "claimed_min_entropy_bits_per_sample": 0.73,
            "adaptive_proportion_window": 512,
        },
    ],
)
def test_sp800_90b_derivation_rejects_invalid_assumptions(
    parameters: dict[str, object],
) -> None:
    script = (
        ROOT
        / "core/skills/qualify-entropy-source/scripts/derive_health_tests.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(parameters),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2


def test_sp800_90b_health_parameters_are_derived_and_checked() -> None:
    request = {
        "alpha": 0.000001,
        "alphabet_size": 2,
        "claimed_min_entropy_bits_per_sample": 0.73,
    }
    parameters = _run(
        "qualify-entropy-source",
        "derive_health_tests.py",
        request,
    )
    assert parameters["formula_version"] == "NIST.SP.800-90B@2018:4.4.1-4.4.2/v1"
    assert 0 < parameters["alpha"] < 1
    assert parameters["alphabet_size"] == 2
    assert parameters["repetition_count_cutoff"] >= 2
    assert parameters["adaptive_proportion_window"] == 1024
    assert parameters["adaptive_proportion_cutoff"] <= 1024

    payload = _fixture("entropy")["qualification_input"]
    payload["health_test_parameters"] = parameters
    payload["source_identity"]["alphabet_size"] = 2
    payload["estimator_invocations"] = [
        {
            "name": "ea_non_iid.py",
            "version": "NIST-90B-2021-05-17",
            "argv": ["python3", "ea_non_iid.py", "-i", "samples.bin"],
            "input_hash": "sha256:" + "1" * 64,
            "output_hash": "sha256:" + "2" * 64,
            "exit_code": 0,
        }
    ]
    qualified = _run(
        "qualify-entropy-source",
        "qualify_run.py",
        payload,
    )
    assert qualified["estimator_invocations"] == payload["estimator_invocations"]
    assert qualified["evidence_state"] == "fail"

    payload["health_test_parameters"]["repetition_count_cutoff"] += 1
    script = (
        ROOT / "core/skills/qualify-entropy-source/scripts/qualify_run.py"
    )
    rejected = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    assert rejected.returncode == 2
    assert "derived SP 800-90B parameters" in rejected.stderr


def test_sp800_90b_nonbinary_alphabet_uses_512_sample_apt_window() -> None:
    parameters = _run(
        "qualify-entropy-source",
        "derive_health_tests.py",
        {
            "alpha": 0.000001,
            "alphabet_size": 4,
            "claimed_min_entropy_bits_per_sample": 1.2,
        },
    )
    assert parameters["adaptive_proportion_window"] == 512


def test_shared_evidence_states_are_distinct_from_decisions() -> None:
    states = {"pass", "fail", "unknown", "not-applicable", "evidence-gap"}
    data = _fixture("entropy")
    assert data["qualification_run_expected"]["evidence_state"] in states
    assert data["requalification_decision_expected"]["evidence_state"] in states
    assert data["qualification_run_expected"]["decision"] not in states
    assert data["requalification_decision_expected"]["decision"] not in states


def test_nist_ir_8547_pin_is_exact_draft_with_source_hash() -> None:
    reference = (
        ROOT
        / "core/skills/plan-pqc-migration/references/authoritative-sources.md"
    ).read_text()
    assert "NIST.IR.8547-IPD@2024-11-12" in reference
    assert "Initial Public Draft" in reference
    assert (
        "sha256:6b551b4ff9858a19c1ab48d7deef2ee52d615066b7d187aaf992cb50c5ca0ed6"
        in reference
    )
