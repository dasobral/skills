from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from skills_export.exporters.codex import (
    export_codex,
    export_codex_marketplace,
    export_codex_plugin,
    export_codex_plugins,
)
from skills_export.manifest import codex_adapter_dir, codex_plugins_dir
from skills_export.validate_codex import validate_codex_plugins


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
    (adapter / "agents").mkdir(parents=True)
    (adapter / "hooks").mkdir()
    (adapter / ".codex-plugin").mkdir()
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
    scripts.mkdir()
    (scripts / "check.py").write_text("print('ok')\n", encoding="utf-8")
    (adapter / ".codex-plugin" / "plugin.json").write_text(
        '{"interface": {"displayName": "Codecraft"}}\n', encoding="utf-8"
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


@pytest.mark.parametrize("flag", ["--no-flat", "--no-bundles"])
def test_codex_cli_rejects_legacy_or_empty_modes(
    repo_copy: Path, flag: str
) -> None:
    from skills_export.cli import main

    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--root",
                str(repo_copy),
                "export",
                "codex",
                flag,
            ]
        )

    assert exc.value.code == 2


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
