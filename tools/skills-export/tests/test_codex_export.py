from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from skills_export.exporters.codex import (
    export_codex,
    export_codex_marketplace,
    export_codex_plugin,
    export_codex_plugins,
)
from skills_export.manifest import codex_adapter_dir, codex_plugins_dir
from skills_export.validate_codex import validate_codex_plugins


EXISTING_CODEX_AGENTS = {
    "codecraft": 2,
    "cpp-qkd-toolkit": 2,
    "agent-platform": 4,
    "aos-stack": 2,
    "scientific-computing": 1,
    "career-writer": 1,
}
CODEX_HOOK_PLUGINS = {
    "codecraft": "SessionStart",
    "cpp-qkd-toolkit": "PreToolUse",
    "aos-stack": "SessionStart",
}
AGENT_ROLE_TERMS = {
    ("codecraft", "code-reviewer"): ("clarity", "security", "evidence"),
    ("codecraft", "convention-analyst"): ("convention", "imperative", "evidence"),
    ("cpp-qkd-toolkit", "cpp-security-reviewer"): (
        "threat model",
        "cryptographic",
        "critical",
    ),
    ("cpp-qkd-toolkit", "cpp-realtime-reviewer"): (
        "concurrency",
        "hot path",
        "data races",
    ),
    ("agent-platform", "reader"): ("reading order", "verbatim", "json array"),
    ("agent-platform", "analyzer"): ("architecture", "risks", "quotation"),
    ("agent-platform", "orchestrator"): ("dependencies", "artifacts", "concurrently"),
    ("agent-platform", "report-writer"): ("executive", "findings", "risks"),
    ("aos-stack", "rust-reviewer"): ("async", "error context", "dependency"),
    ("aos-stack", "inference-advisor"): ("vram", "vllm", "litellm"),
    ("scientific-computing", "platform-designer"): (
        "scientific",
        "infrastructure",
        "kernels",
    ),
    ("career-writer", "document-editor"): ("audience", "credentials", "invent"),
}
OUTPUT_TYPES_TEXT = (
    "`json_object`, `markdown_document`, `file_write`, `inline_text`, "
    "or `tool_call_sequence`"
)


def _write_codex_overlay(root: Path, plugin_name: str = "codecraft") -> None:
    manifest = yaml.safe_load(
        (root / "core" / "manifest.yaml").read_text(encoding="utf-8")
    )
    for skill_name in manifest["plugins"][plugin_name]["skills"]:
        skill = root / "core" / "skills" / skill_name
        if not skill.exists():
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {skill_name}\ndescription: Temporary test skill.\n---\n",
                encoding="utf-8",
            )

    adapter = root / "adapters" / "codex" / plugin_name
    (adapter / "agents").mkdir(parents=True, exist_ok=True)
    (adapter / "hooks").mkdir(exist_ok=True)
    (adapter / ".codex-plugin").mkdir(exist_ok=True)
    (adapter / "agents" / "code-reviewer.toml").write_text(
        'name = "code-reviewer"\n'
        'description = "Review code."\n'
        'developer_instructions = "Review independently."\n',
        encoding="utf-8",
    )
    (adapter / "hooks" / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": "startup|resume",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": (
                                        "python3 ${PLUGIN_ROOT}/hooks/"
                                        "scripts/check.py"
                                    ),
                                }
                            ],
                        }
                    ]
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    scripts = adapter / "hooks" / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "check.py").write_text("print('ok')\n", encoding="utf-8")
    display_name = manifest["plugins"][plugin_name]["display_name"]
    (adapter / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"interface": {"displayName": display_name}}) + "\n",
        encoding="utf-8",
    )

    shared = (
        root
        / "adapters"
        / "codex"
        / "_shared"
        / "skills"
        / "install-plugin-agents"
    )
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "SKILL.md").write_text(
        "---\n"
        "name: install-plugin-agents\n"
        "description: Install bundled Codex agent templates.\n"
        "---\n",
        encoding="utf-8",
    )


def _limit_manifest(root: Path, names: list[str]) -> None:
    path = root / "core" / "manifest.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["plugins"] = {
        name: manifest["plugins"][name] for name in names
    }
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def test_codex_path_helpers(repo_copy: Path) -> None:
    assert codex_adapter_dir(repo_copy, "codecraft") == (
        repo_copy / "adapters" / "codex" / "codecraft"
    )
    assert codex_plugins_dir(repo_copy) == repo_copy / "plugins" / "codex"


def test_existing_plugins_have_complete_codex_agent_templates(
    repo_copy: Path,
) -> None:
    _limit_manifest(repo_copy, list(EXISTING_CODEX_AGENTS))

    for plugin_name, expected_count in EXISTING_CODEX_AGENTS.items():
        plugin = export_codex_plugin(
            repo_copy, plugin_name, repo_copy / "plugins" / "codex"
        )
        agent_files = sorted((plugin / "agents").glob("*.toml"))
        assert len(agent_files) == expected_count, plugin_name
        for agent_file in agent_files:
            data = tomllib.loads(agent_file.read_text(encoding="utf-8"))
            assert data["name"] == agent_file.stem
            for key in ("name", "description", "developer_instructions"):
                assert isinstance(data.get(key), str)
                assert data[key].strip()
            text = agent_file.read_text(encoding="utf-8")
            assert not re.search(r"(?m)^\s*model\s*=", text)
            assert "Task tool" not in text
            assert "subagent_type" not in text
            semantic_text = (
                f"{data['description']}\n{data['developer_instructions']}".lower()
            )
            for term in AGENT_ROLE_TERMS[(plugin_name, data["name"])]:
                assert term in semantic_text, (plugin_name, data["name"], term)


def test_existing_plugins_have_codex_metadata_overlays() -> None:
    adapters = Path(__file__).parents[3] / "adapters" / "codex"

    for plugin_name in EXISTING_CODEX_AGENTS:
        overlay_path = adapters / plugin_name / ".codex-plugin" / "plugin.json"
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        assert set(overlay) == {"interface"}
        assert isinstance(overlay["interface"].get("displayName"), str)
        assert overlay["interface"]["displayName"].strip()


def test_existing_plugin_hooks_use_native_codex_schema(repo_copy: Path) -> None:
    _limit_manifest(repo_copy, list(EXISTING_CODEX_AGENTS))

    for plugin_name, expected_event in CODEX_HOOK_PLUGINS.items():
        plugin = export_codex_plugin(
            repo_copy, plugin_name, repo_copy / "plugins" / "codex"
        )
        hooks_path = plugin / "hooks" / "hooks.json"
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
        assert set(data) == {"hooks"}
        assert set(data["hooks"]) == {expected_event}
        for group in data["hooks"][expected_event]:
            assert set(group) <= {"matcher", "hooks"}
            assert group["hooks"]
            for handler in group["hooks"]:
                assert handler["type"] == "command"
                assert handler["command"].startswith("python3 ${PLUGIN_ROOT}/")
                assert 0 < handler["timeout"] <= 10
                assert set(handler) <= {
                    "type",
                    "command",
                    "timeout",
                    "statusMessage",
                }

    for plugin_name in set(EXISTING_CODEX_AGENTS) - set(CODEX_HOOK_PLUGINS):
        assert not (repo_copy / "adapters" / "codex" / plugin_name / "hooks").exists()


def test_existing_plugin_codex_metadata_matches_exported_components(
    repo_copy: Path,
) -> None:
    _limit_manifest(repo_copy, list(EXISTING_CODEX_AGENTS))
    manifest = yaml.safe_load(
        (repo_copy / "core" / "manifest.yaml").read_text(encoding="utf-8")
    )

    for plugin_name in EXISTING_CODEX_AGENTS:
        plugin = export_codex_plugin(
            repo_copy, plugin_name, repo_copy / "plugins" / "codex"
        )
        plugin_json = json.loads(
            (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        metadata = manifest["plugins"][plugin_name]["codex"]
        assert metadata["agents"] is (plugin / "agents").is_dir()
        assert metadata["hooks"] is (plugin / "hooks" / "hooks.json").is_file()
        assert ("hooks" in plugin_json) is metadata["hooks"]


@pytest.mark.parametrize(
    ("plugin_name", "script_name", "event", "hook_input", "expected_fragment"),
    [
        (
            "codecraft",
            "check_conventions_age.py",
            "SessionStart",
            {"hook_event_name": "SessionStart", "source": "startup"},
            "CODING_REQUIREMENTS.md is",
        ),
        (
            "cpp-qkd-toolkit",
            "cpp_security_hint.py",
            "PreToolUse",
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "apply_patch",
                "tool_input": {
                    "command": "*** Update File: src/key_store.cpp\n+ log(nonce);"
                },
            },
            "security-sensitive",
        ),
        (
            "aos-stack",
            "detect_gpu.py",
            "SessionStart",
            {"hook_event_name": "SessionStart", "source": "startup"},
            "GPU detected",
        ),
    ],
)
def test_codex_hooks_emit_native_additional_context(
    repo_copy: Path,
    plugin_name: str,
    script_name: str,
    event: str,
    hook_input: dict[str, object],
    expected_fragment: str,
) -> None:
    script = (
        repo_copy
        / "adapters"
        / "codex"
        / plugin_name
        / "hooks"
        / "scripts"
        / script_name
    )
    if plugin_name == "codecraft":
        requirements = repo_copy / "CODING_REQUIREMENTS.md"
        requirements.write_text("# Conventions\n", encoding="utf-8")
        old = 1_600_000_000
        os.utime(requirements, (old, old))
    environment = os.environ.copy()
    if plugin_name == "aos-stack":
        binary_dir = repo_copy / "test-bin"
        binary_dir.mkdir()
        nvidia_smi = binary_dir / "nvidia-smi"
        nvidia_smi.write_text(
            "#!/bin/sh\nprintf 'Test GPU, 24576 MiB\\n'\n", encoding="utf-8"
        )
        nvidia_smi.chmod(0o755)
        environment["PATH"] = f"{binary_dir}{os.pathsep}{environment['PATH']}"

    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
        check=True,
        cwd=repo_copy,
        env=environment,
    )
    output = json.loads(completed.stdout)
    assert set(output) == {"hookSpecificOutput"}
    assert output["hookSpecificOutput"]["hookEventName"] == event
    assert expected_fragment in output["hookSpecificOutput"]["additionalContext"]


def test_codecraft_hook_resolves_git_root_and_ignores_cursor_control_files(
    repo_copy: Path,
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo_copy, check=True)
    nested = repo_copy / "packages" / "service"
    nested.mkdir(parents=True)
    cursor_requirements = repo_copy / ".cursor" / "CODING_REQUIREMENTS.md"
    cursor_requirements.parent.mkdir()
    cursor_requirements.write_text("# Cursor-only\n", encoding="utf-8")
    codex_requirements = repo_copy / ".codex" / "CODING_REQUIREMENTS.md"
    codex_requirements.parent.mkdir()
    codex_requirements.write_text("# Codex\n", encoding="utf-8")
    old = 1_600_000_000
    os.utime(cursor_requirements, (old, old))
    script = (
        repo_copy
        / "adapters"
        / "codex"
        / "codecraft"
        / "hooks"
        / "scripts"
        / "check_conventions_age.py"
    )
    hook_input = {
        "hook_event_name": "SessionStart",
        "source": "startup",
        "cwd": str(nested),
    }

    fresh = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
        check=True,
        cwd=nested,
    )
    assert fresh.stdout == ""
    assert fresh.stderr == ""

    os.utime(codex_requirements, (old, old))
    stale = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
        check=True,
        cwd=nested,
    )
    output = json.loads(stale.stdout)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert ".codex/CODING_REQUIREMENTS.md" in context
    assert ".cursor" not in context


@pytest.mark.parametrize(
    ("plugin_name", "script_name", "valid_input"),
    [
        (
            "codecraft",
            "check_conventions_age.py",
            {"hook_event_name": "SessionStart", "cwd": "."},
        ),
        (
            "cpp-qkd-toolkit",
            "cpp_security_hint.py",
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "apply_patch",
                "tool_input": {"command": "*** Update File: README.md\n+ secret"},
            },
        ),
        (
            "aos-stack",
            "detect_gpu.py",
            {"hook_event_name": "SessionStart", "cwd": "."},
        ),
    ],
)
def test_codex_hooks_noop_safely_for_irrelevant_and_invalid_input(
    repo_copy: Path,
    plugin_name: str,
    script_name: str,
    valid_input: dict[str, object],
) -> None:
    script = (
        repo_copy
        / "adapters"
        / "codex"
        / plugin_name
        / "hooks"
        / "scripts"
        / script_name
    )
    environment = os.environ.copy()
    if plugin_name == "aos-stack":
        environment["PATH"] = ""

    for hook_input in (json.dumps(valid_input), "{invalid-json"):
        completed = subprocess.run(
            [sys.executable, str(script)],
            input=hook_input,
            text=True,
            capture_output=True,
            check=True,
            cwd=repo_copy,
            env=environment,
        )
        assert completed.stdout == ""
        assert completed.stderr == ""


def test_portable_convention_reference_has_no_platform_control_paths() -> None:
    root = Path(__file__).parents[3]
    portable_skill = root / "core" / "skills" / "write-conformant-code"
    portable_paths = [
        portable_skill / "SKILL.md",
        portable_skill / "references" / "repository-conventions.md",
    ]
    codex_hook = (
        root
        / "adapters"
        / "codex"
        / "codecraft"
        / "hooks"
        / "scripts"
        / "check_conventions_age.py"
    ).read_text(encoding="utf-8")

    for path in portable_paths:
        assert ".cursor" not in path.read_text(encoding="utf-8").lower()
    assert ".cursor" not in codex_hook.lower()
    assert ".codex/CODING_REQUIREMENTS.md" in codex_hook


def test_codex_adapter_readme_documents_native_plugin_architecture() -> None:
    readme = (
        Path(__file__).parents[3] / "adapters" / "codex" / "README.md"
    ).read_text(encoding="utf-8")

    assert ".codex-plugin/plugin.json" in readme
    assert "plugins/codex/" in readme
    assert "hooks/hooks.json" in readme
    assert "bundle.json" not in readme
    assert ".agents/instructions.md" not in readme


def test_each_codex_adapter_authors_complete_operational_readme(
    repo_copy: Path,
) -> None:
    manifest = yaml.safe_load(
        (repo_copy / "core" / "manifest.yaml").read_text(encoding="utf-8")
    )
    required_sections = (
        "## Daily workflow",
        "## Triggers",
        "## Required inputs",
        "## Artifacts",
        "## Agent authority",
        "## Deterministic checks and agent decisions",
        "## Data guarantees",
        "## Limitations and non-claims",
    )

    for plugin_name, metadata in manifest["plugins"].items():
        authored = repo_copy / "adapters" / "codex" / plugin_name / "README.md"
        assert authored.is_file(), plugin_name
        text = authored.read_text(encoding="utf-8")
        for section in required_sections:
            assert section in text, (plugin_name, section)
        for skill_name in metadata["skills"]:
            assert f"`{skill_name}`" in text, (plugin_name, skill_name)

        generated = export_codex_plugin(
            repo_copy,
            plugin_name,
            repo_copy / "plugins" / "codex",
        )
        assert (generated / "README.md").read_bytes() == authored.read_bytes()


def test_create_agent_skill_is_platform_aware() -> None:
    root = Path(__file__).parents[3]
    skill = (root / "core" / "skills" / "create-agent" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    conventions = (
        root
        / "core"
        / "skills"
        / "create-agent"
        / "references"
        / "agent-conventions.md"
    ).read_text(encoding="utf-8")

    assert "unknown platform" in skill.lower()
    assert ".codex/agents/<name>.toml" in skill
    assert "developer_instructions" in skill
    assert 'name = "agent-name"' in conventions
    assert 'description = "' in conventions
    assert 'developer_instructions = """' in conventions


def test_create_agent_uses_one_exact_output_vocabulary() -> None:
    root = Path(__file__).parents[3] / "core" / "skills" / "create-agent"
    paths = [
        root / "SKILL.md",
        root / "references" / "agent-conventions.md",
        root / "templates" / "agent-definition.md",
        root / "templates" / "agent-definition.toml",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert OUTPUT_TYPES_TEXT in text, path


def test_generated_codex_agent_satisfies_documented_contract(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[3] / "core" / "skills" / "create-agent"
    template = (root / "templates" / "agent-definition.toml").read_text(
        encoding="utf-8"
    )
    replacements = {
        "{{AGENT_NAME}}": "summarizer",
        "{{DESCRIPTION}}": "Summarizes one document with traceable evidence.",
        "{{ROLE}}": "You are a document summarization specialist.",
        "{{INPUTS}}": "Receive one document_path string.",
        "{{PROCESS}}": "Read the document, identify claims, and construct output.",
        "{{OUTPUT_TYPE}}": "json_object",
        "{{OUTPUT_CONTRACT}}": "Return title, claims, and source locations.",
        "{{CONSTRAINTS}}": "Do not invent claims or modify the source.",
        "{{INTEGRATION}}": "Return the JSON object directly to the caller.",
    }
    generated = template
    for placeholder, value in replacements.items():
        generated = generated.replace(placeholder, value)
    assert "{{" not in generated
    destination = tmp_path / ".codex" / "agents" / "summarizer.toml"
    destination.parent.mkdir(parents=True)
    destination.write_text(generated, encoding="utf-8")

    data = tomllib.loads(destination.read_text(encoding="utf-8"))
    assert data["name"] == destination.stem
    assert data["description"] == replacements["{{DESCRIPTION}}"]
    instructions = data["developer_instructions"]
    for heading in (
        "Role",
        "Inputs",
        "Process",
        "Output Contract",
        "Constraints",
        "Integration Hooks",
    ):
        assert f"## {heading}" in instructions
    match = re.search(r"Output type: `([^`]+)`", instructions)
    assert match
    assert match.group(1) in {
        "json_object",
        "markdown_document",
        "file_write",
        "inline_text",
        "tool_call_sequence",
    }


def test_native_export_creates_codex_layout(repo_copy: Path) -> None:
    _write_codex_overlay(repo_copy)

    plugin = export_codex_plugin(
        repo_copy, "codecraft", repo_copy / "plugins" / "codex"
    )

    assert (plugin / ".codex-plugin" / "plugin.json").is_file()
    assert (plugin / "skills" / "analyze-codebase" / "SKILL.md").is_file()
    assert (plugin / "agents" / "code-reviewer.toml").is_file()
    assert (
        plugin / "skills" / "install-plugin-agents" / "SKILL.md"
    ).is_file()
    assert (
        plugin
        / "skills"
        / "install-plugin-agents"
        / "scripts"
        / "agent_installer.py"
    ).is_file()
    manifest = json.loads(
        (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["name"] == "codecraft"
    assert manifest["skills"] == "./skills/"
    assert manifest["hooks"] == "./hooks/hooks.json"
    for key in ("skills", "hooks"):
        assert manifest[key].startswith("./")


def test_export_all_plugins_and_marketplace(repo_copy: Path) -> None:
    manifest = yaml.safe_load(
        (repo_copy / "core" / "manifest.yaml").read_text(encoding="utf-8")
    )
    names = list(manifest["plugins"])
    assert len(names) == 11
    for name in names:
        _write_codex_overlay(repo_copy, name)

    export_codex_plugins(repo_copy)

    assert {
        path.name for path in (repo_copy / "plugins" / "codex").iterdir()
    } == set(names)
    marketplace = json.loads(
        (repo_copy / ".agents" / "plugins" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    entries = marketplace["plugins"]
    assert len(entries) == len(names)
    assert len({entry["name"] for entry in entries}) == len(names)
    assert [entry["name"] for entry in entries] == names
    assert all(
        entry["source"]["path"] == f"./plugins/codex/{entry['name']}"
        for entry in entries
    )
    assert all(entry["source"]["source"] == "local" for entry in entries)
    assert all(
        entry["policy"]
        == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
        for entry in entries
    )
    assert all(isinstance(entry["category"], str) and entry["category"] for entry in entries)
    assert validate_codex_plugins(repo_copy) == []


def test_clean_and_repeatable_native_export(repo_copy: Path) -> None:
    _write_codex_overlay(repo_copy)
    output = repo_copy / "plugins" / "codex"
    plugin = export_codex_plugin(repo_copy, "codecraft", output)
    (plugin / "stale.txt").write_text("stale", encoding="utf-8")

    export_codex_plugin(repo_copy, "codecraft", output)
    first = _snapshot(plugin)
    export_codex_plugin(repo_copy, "codecraft", output)

    assert "stale.txt" not in first
    assert _snapshot(plugin) == first


def test_flat_export_is_preserved_without_legacy_bundles(repo_copy: Path) -> None:
    _limit_manifest(repo_copy, ["codecraft"])
    destination = repo_copy / "dist" / "codex"

    export_codex(
        repo_copy,
        flat_output_dir=destination,
        native_output_dir=None,
        plugins=["codecraft"],
    )

    assert (destination / "skills" / "analyze-codebase" / "SKILL.md").is_file()
    assert not list(destination.rglob("bundle.json"))
    assert not list(destination.rglob("AGENTS.md"))


def test_legacy_bundles_flag_fails_explicitly(repo_copy: Path) -> None:
    _limit_manifest(repo_copy, ["codecraft"])
    destination = repo_copy / "dist" / "codex"

    with pytest.raises(ValueError, match="legacy Codex bundles"):
        export_codex(
            repo_copy,
            destination,
            plugins=["codecraft"],
            flat=True,
            bundles=True,
        )

    assert not destination.exists()


def test_codex_export_rejects_no_artifact_request(repo_copy: Path) -> None:
    with pytest.raises(ValueError, match="no artifacts"):
        export_codex(repo_copy, flat=False, native=False)


def test_codex_cli_export_writes_flat_skills(repo_copy: Path) -> None:
    from skills_export.cli import main

    assert main(
        [
            "--root",
            str(repo_copy),
            "export",
            "codex",
            "--plugin",
            "career-writer",
        ]
    ) == 0

    assert (
        repo_copy
        / "dist"
        / "codex"
        / "skills"
        / "career-documents"
        / "SKILL.md"
    ).is_file()


def test_overlay_cannot_relocate_generated_components(repo_copy: Path) -> None:
    _write_codex_overlay(repo_copy)
    overlay_path = (
        repo_copy
        / "adapters"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    )
    overlay_path.write_text(
        '{"skills": "./other/", "hooks": "./other/hooks.json"}\n',
        encoding="utf-8",
    )

    plugin = export_codex_plugin(
        repo_copy, "codecraft", repo_copy / "plugins" / "codex"
    )
    manifest = json.loads(
        (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )

    assert manifest["skills"] == "./skills/"
    assert manifest["hooks"] == "./hooks/hooks.json"


@pytest.mark.parametrize(
    "field,value",
    [
        ("skills", "skills/"),
        ("hooks", "/tmp/hooks.json"),
        ("hooks", "./hooks/../../outside.json"),
    ],
)
def test_manifest_rejects_unsafe_component_paths(
    repo_copy: Path, field: str, value: str
) -> None:
    _write_codex_overlay(repo_copy)
    overlay_path = (
        repo_copy
        / "adapters"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    )
    overlay_path.write_text(json.dumps({field: value}), encoding="utf-8")

    with pytest.raises(ValueError, match="component path"):
        export_codex_plugin(
            repo_copy, "codecraft", repo_copy / "plugins" / "codex"
        )


def test_invalid_plugin_name_is_rejected_before_target_delete(
    repo_copy: Path,
) -> None:
    manifest_path = repo_copy / "core" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["plugins"]["../escape"] = dict(manifest["plugins"]["codecraft"])
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    escaped_target = repo_copy / "plugins" / "escape"
    escaped_target.mkdir(parents=True)
    sentinel = escaped_target / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="plugin name"):
        export_codex_plugin(
            repo_copy,
            "../escape",
            repo_copy / "plugins" / "codex",
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_output_target_symlink_is_rejected_before_clean(
    repo_copy: Path,
) -> None:
    _write_codex_overlay(repo_copy)
    output = repo_copy / "plugins" / "codex"
    output.mkdir(parents=True)
    outside = repo_copy / "outside-output"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    (output / "codecraft").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="output"):
        export_codex_plugin(repo_copy, "codecraft", output)

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_adapter_root_symlink_is_rejected(repo_copy: Path) -> None:
    _write_codex_overlay(repo_copy)
    adapter = repo_copy / "adapters" / "codex" / "codecraft"
    outside = repo_copy / "outside-adapter"
    adapter.rename(outside)
    adapter.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        export_codex_plugin(
            repo_copy, "codecraft", repo_copy / "plugins" / "codex"
        )


def test_nested_adapter_symlink_is_rejected(repo_copy: Path) -> None:
    _write_codex_overlay(repo_copy)
    adapter = repo_copy / "adapters" / "codex" / "codecraft"
    assets = adapter / "assets"
    assets.mkdir()
    (assets / "linked-agents").symlink_to(
        adapter / "agents", target_is_directory=True
    )

    with pytest.raises(ValueError, match="symlink"):
        export_codex_plugin(
            repo_copy, "codecraft", repo_copy / "plugins" / "codex"
        )


def test_core_skill_source_symlink_is_rejected(repo_copy: Path) -> None:
    _write_codex_overlay(repo_copy)
    skill = repo_copy / "core" / "skills" / "analyze-codebase"
    outside = repo_copy / "outside-reference.md"
    outside.write_text("outside", encoding="utf-8")
    (skill / "linked-reference.md").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        export_codex_plugin(
            repo_copy, "codecraft", repo_copy / "plugins" / "codex"
        )


def test_bulk_export_validates_all_names_before_clean(repo_copy: Path) -> None:
    manifest_path = repo_copy / "core" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["plugins"]["../escape"] = dict(manifest["plugins"]["codecraft"])
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    output = repo_copy / "plugins" / "codex"
    output.mkdir(parents=True)
    sentinel = output / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="plugin name"):
        export_codex_plugins(repo_copy, output)

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_native_output_root_must_stay_inside_repository(
    repo_copy: Path, tmp_path: Path
) -> None:
    _write_codex_overlay(repo_copy)
    outside = tmp_path / "external-output"

    with pytest.raises(ValueError, match="repository"):
        export_codex_plugin(repo_copy, "codecraft", outside)

    assert not outside.exists()


def test_marketplace_output_parent_symlink_is_rejected(
    repo_copy: Path,
) -> None:
    outside = repo_copy / "outside-marketplace"
    outside.mkdir()
    agents = repo_copy / ".agents"
    agents.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="marketplace.*symlink"):
        export_codex_marketplace(repo_copy)

    assert not (outside / "plugins" / "marketplace.json").exists()


def test_marketplace_output_file_symlink_is_rejected(
    repo_copy: Path,
) -> None:
    destination = repo_copy / ".agents" / "plugins" / "marketplace.json"
    destination.parent.mkdir(parents=True)
    outside = repo_copy / "outside-marketplace.json"
    outside.write_text("keep", encoding="utf-8")
    destination.symlink_to(outside)

    with pytest.raises(ValueError, match="marketplace.*symlink"):
        export_codex_marketplace(repo_copy)

    assert outside.read_text(encoding="utf-8") == "keep"


def test_flat_export_rejects_source_symlink_before_clean(
    repo_copy: Path,
) -> None:
    _limit_manifest(repo_copy, ["codecraft"])
    skill = repo_copy / "core" / "skills" / "analyze-codebase"
    target = skill / "SKILL.md"
    (skill / "linked-skill.md").symlink_to(target)
    destination = repo_copy / "dist" / "codex"
    flat = destination / "skills"
    flat.mkdir(parents=True)
    sentinel = flat / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="symlink"):
        export_codex(
            repo_copy,
            flat_output_dir=destination,
            plugins=["codecraft"],
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_marketplace_validates_plugin_names_before_output(
    repo_copy: Path,
) -> None:
    manifest_path = repo_copy / "core" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["plugins"]["../escape"] = dict(manifest["plugins"]["codecraft"])
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="plugin name"):
        export_codex_marketplace(repo_copy)

    assert not (repo_copy / ".agents").exists()


@pytest.mark.parametrize("container", ["adapters", "core"])
def test_export_rejects_symlinked_source_container_ancestor(
    repo_copy: Path,
    container: str,
) -> None:
    _write_codex_overlay(repo_copy)
    source = repo_copy / container
    backing = repo_copy / f"real-{container}"
    source.rename(backing)
    source.symlink_to(backing, target_is_directory=True)

    with pytest.raises(ValueError, match="ancestor.*symlink"):
        export_codex_plugin(
            repo_copy,
            "codecraft",
            repo_copy / "plugins" / "codex",
        )


def test_export_rejects_symlinked_repository_root(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    linked_root = tmp_path / "linked-repo"
    linked_root.symlink_to(repo_copy, target_is_directory=True)

    with pytest.raises(ValueError, match="repository root.*symlink"):
        export_codex_plugin(
            linked_root,
            "codecraft",
            linked_root / "plugins" / "codex",
        )


def test_export_rejects_interface_asset_traversal_before_clean(
    repo_copy: Path,
) -> None:
    _write_codex_overlay(repo_copy)
    overlay = (
        repo_copy
        / "adapters"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    )
    overlay.write_text(
        json.dumps(
            {
                "interface": {
                    "displayName": "Codecraft",
                    "logo": "./../outside.png",
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = repo_copy / "plugins" / "codex"
    existing = output / "codecraft"
    existing.mkdir(parents=True)
    sentinel = existing / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="interface.*logo"):
        export_codex_plugin(repo_copy, "codecraft", output)

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_export_copies_and_emits_mcp_and_app_components(
    repo_copy: Path,
) -> None:
    _write_codex_overlay(repo_copy)
    adapter = repo_copy / "adapters" / "codex" / "codecraft"
    (adapter / ".mcp.json").write_text(
        '{"mcp_servers": {"review": {"command": "review-server"}}}\n',
        encoding="utf-8",
    )
    (adapter / ".app.json").write_text(
        '{"id": "plugin_asdk_app_review"}\n',
        encoding="utf-8",
    )
    overlay = adapter / ".codex-plugin" / "plugin.json"
    overlay.write_text(
        json.dumps(
            {
                "mcpServers": "./.mcp.json",
                "apps": "./.app.json",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    plugin = export_codex_plugin(
        repo_copy,
        "codecraft",
        repo_copy / "plugins" / "codex",
    )
    manifest = json.loads(
        (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )

    assert manifest["mcpServers"] == "./.mcp.json"
    assert manifest["apps"] == "./.app.json"
    assert (plugin / ".mcp.json").is_file()
    assert (plugin / ".app.json").is_file()


def test_export_rejects_missing_mcp_component_before_clean(
    repo_copy: Path,
) -> None:
    _write_codex_overlay(repo_copy)
    adapter = repo_copy / "adapters" / "codex" / "codecraft"
    overlay = adapter / ".codex-plugin" / "plugin.json"
    overlay.write_text('{"mcpServers": "./missing.mcp.json"}\n', encoding="utf-8")
    output = repo_copy / "plugins" / "codex"
    existing = output / "codecraft"
    existing.mkdir(parents=True)
    sentinel = existing / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="mcpServers"):
        export_codex_plugin(repo_copy, "codecraft", output)

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_native_export_is_deterministic_across_python_hash_seeds(
    repo_copy: Path,
) -> None:
    _write_codex_overlay(repo_copy)
    overlay = (
        repo_copy
        / "adapters"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    )
    overlay.write_text(
        json.dumps(
            {
                "homepage": "https://example.test/codecraft",
                "repository": "https://example.test/repository",
                "interface": {"displayName": "Codecraft"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    script = (
        "import hashlib,json,pathlib,sys;"
        "from skills_export.exporters.codex import export_codex_plugin;"
        "root=pathlib.Path(sys.argv[1]);"
        "plugin=export_codex_plugin(root,'codecraft',root/'plugins'/'codex');"
        "print(json.dumps([(str(p.relative_to(plugin)),"
        "hashlib.sha256(p.read_bytes()).hexdigest()) "
        "for p in sorted(plugin.rglob('*')) if p.is_file()]))"
    )
    outputs = []
    for seed in ("1", "2", "8675309"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        completed = subprocess.run(
            [sys.executable, "-c", script, str(repo_copy)],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        outputs.append(completed.stdout)

    assert len(set(outputs)) == 1
