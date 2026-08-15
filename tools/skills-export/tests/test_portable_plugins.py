from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from skills_export.cli import main
from skills_export.manifest import load_manifest, plugin_skill_names, skills_dir
from skills_export.portable import (
    AGENT_PLUGINS_SCHEMA,
    export_portable_all,
    portable_plugin_manifest,
    validate_portable_plugins,
)


SCHEMA = json.loads(
    (
        Path(__file__).parents[1]
        / "skills_export"
        / "schemas"
        / "plugin.schema.json"
    ).read_text(encoding="utf-8")
)


def test_skills_live_at_well_known_path(repo_copy: Path) -> None:
    assert (skills_dir(repo_copy) / "analyze-codebase" / "SKILL.md").is_file()
    assert not (repo_copy / "core" / "skills").exists()


def test_export_portable_plugins_writes_schema_valid_symlinks(repo_copy: Path) -> None:
    paths = export_portable_all(repo_copy)
    manifest = load_manifest(repo_copy)
    assert len(paths) == len(manifest["plugins"])
    validator = Draft202012Validator(SCHEMA)
    for name, meta in manifest["plugins"].items():
        plugin_json = json.loads(
            (repo_copy / "plugins" / name / "plugin.json").read_text(encoding="utf-8")
        )
        validator.validate(plugin_json)
        assert plugin_json["$schema"] == AGENT_PLUGINS_SCHEMA
        assert plugin_json["name"] == name
        assert plugin_json["version"] == str(meta["version"])
        for skill in plugin_skill_names(manifest, name):
            link = repo_copy / "plugins" / name / "skills" / skill
            assert link.is_symlink()
            assert (link / "SKILL.md").is_file()
            assert (link / "SKILL.md").resolve() == (
                repo_copy / "skills" / skill / "SKILL.md"
            ).resolve()
    assert validate_portable_plugins(repo_copy) == []


def test_portable_manifest_omits_vendor_fields() -> None:
    data = portable_plugin_manifest(
        "codecraft",
        {
            "version": "2.1.0",
            "description": "Quality pipeline",
            "keywords": ["review"],
            "display_name": "Codecraft",
            "category": "developer-tools",
            "tags": ["style"],
        },
        {"license": "MIT", "author": {"name": "Test"}},
    )
    assert set(data) <= {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "license",
        "keywords",
        "homepage",
        "repository",
        "extensions",
    }
    Draft202012Validator(SCHEMA).validate(data)


def test_cli_validate_after_portable_export(repo_copy: Path) -> None:
    assert main(["--root", str(repo_copy), "export", "cursor", "--plugin", "career-writer"]) == 0
    assert main(["--root", str(repo_copy), "validate"]) == 0


def test_adapter_helper_skills_are_internal() -> None:
    root = Path(__file__).parents[3]
    internals = [
        root
        / "adapters/codex/_shared/skills/install-plugin-agents/SKILL.md",
        root
        / "adapters/codex/crypto-change-radar/skills/check-crypto-runtime/SKILL.md",
        root
        / "adapters/codex/entropy-flight-recorder/skills/check-entropy-runtime/SKILL.md",
        root / "landing/examples/sample-landing-skill/SKILL.md",
    ]
    for path in internals:
        text = path.read_text(encoding="utf-8")
        assert "internal: true" in text
