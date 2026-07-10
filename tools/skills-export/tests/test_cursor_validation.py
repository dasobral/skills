from __future__ import annotations

import json
from pathlib import Path

from skills_export.cli import main
from skills_export.exporters.cursor import export_cursor


def _messages(issues: list[object]) -> list[str]:
    return [issue.message for issue in issues]


def test_generated_cursor_plugins_validate_against_core_manifest(
    repo_copy: Path,
) -> None:
    from skills_export.validate_cursor import validate_cursor_plugins

    export_cursor(
        repo_copy,
        repo_copy / "plugins" / "cursor",
        sync_root=True,
    )

    assert {
        path.name
        for path in (repo_copy / "plugins" / "cursor").iterdir()
        if path.is_dir()
    } == {
        "codecraft",
        "cpp-qkd-toolkit",
        "agent-platform",
        "aos-stack",
        "scientific-computing",
        "career-writer",
    }
    assert validate_cursor_plugins(repo_copy) == []


def test_cursor_clean_sync_removes_plugins_without_cursor_metadata(
    repo_copy: Path,
) -> None:
    output = repo_copy / "plugins" / "cursor"
    codex_only = {
        "agentic-trust-gate",
        "agent-attack-replay",
        "crypto-change-radar",
        "entropy-flight-recorder",
        "scientific-claim-ledger",
    }
    for name in codex_only:
        stale = output / name
        stale.mkdir(parents=True)
        (stale / "stale.txt").write_text("stale", encoding="utf-8")

    export_cursor(repo_copy, output, sync_root=True)

    assert not any((output / name).exists() for name in codex_only)
    marketplace = json.loads(
        (repo_copy / ".cursor-plugin" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    assert [entry["name"] for entry in marketplace["plugins"]] == [
        "codecraft",
        "cpp-qkd-toolkit",
        "agent-platform",
        "aos-stack",
        "scientific-computing",
        "career-writer",
    ]


def test_cursor_validation_rejects_unsafe_component_path(
    repo_copy: Path,
) -> None:
    from skills_export.validate_cursor import validate_cursor_plugins

    export_cursor(
        repo_copy,
        repo_copy / "plugins" / "cursor",
        sync_root=True,
    )
    manifest_path = (
        repo_copy
        / "plugins"
        / "cursor"
        / "codecraft"
        / ".cursor-plugin"
        / "plugin.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["skills"] = "./skills/../../outside"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert any(
        "component path 'skills' must not contain '..'" in message
        for message in _messages(validate_cursor_plugins(repo_copy))
    )


def test_cursor_validation_checks_skill_frontmatter(
    repo_copy: Path,
) -> None:
    from skills_export.validate_cursor import validate_cursor_plugins

    export_cursor(
        repo_copy,
        repo_copy / "plugins" / "cursor",
        sync_root=True,
    )
    skill = (
        repo_copy
        / "plugins"
        / "cursor"
        / "codecraft"
        / "skills"
        / "analyze-codebase"
        / "SKILL.md"
    )
    skill.write_text("# Missing frontmatter\n", encoding="utf-8")

    assert "skill is missing YAML frontmatter" in _messages(
        validate_cursor_plugins(repo_copy)
    )


def test_cursor_validation_checks_marketplace_order_and_sources(
    repo_copy: Path,
) -> None:
    from skills_export.validate_cursor import validate_cursor_plugins

    export_cursor(
        repo_copy,
        repo_copy / "plugins" / "cursor",
        sync_root=True,
    )
    marketplace_path = repo_copy / ".cursor-plugin" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    marketplace["plugins"][0]["source"] = "plugins/cursor/not-codecraft"
    marketplace["plugins"].reverse()
    marketplace_path.write_text(json.dumps(marketplace), encoding="utf-8")

    messages = _messages(validate_cursor_plugins(repo_copy))
    assert "marketplace source does not match generated plugin" in messages
    assert "marketplace plugin order does not match core manifest" in messages


def test_validate_cursor_cli_and_default_validate_generated_cursor(
    repo_copy: Path,
    capsys,
) -> None:
    export_cursor(
        repo_copy,
        repo_copy / "plugins" / "cursor",
        sync_root=True,
    )

    assert main(["--root", str(repo_copy), "validate", "cursor"]) == 0
    assert "Cursor validation OK: 6 generated plugin(s)" in capsys.readouterr().out
    (
        repo_copy
        / "plugins"
        / "cursor"
        / "codecraft"
        / ".cursor-plugin"
        / "plugin.json"
    ).write_text("{}\n", encoding="utf-8")
    assert main(["--root", str(repo_copy), "validate"]) == 1


def test_sync_cli_reports_six_cursor_plugins_and_eleven_codex_plugins(
    repo_copy: Path,
    capsys,
) -> None:
    assert main(["--root", str(repo_copy), "sync", "cursor"]) == 0
    assert "Synced 6 Cursor plugin(s)" in capsys.readouterr().out

    assert main(["--root", str(repo_copy), "sync", "codex"]) == 0
    assert "Synced 11 Codex plugin(s)" in capsys.readouterr().out


def test_cursor_validation_rejects_symlinked_plugin_directory(
    repo_copy: Path,
) -> None:
    from skills_export.validate_cursor import validate_cursor_plugins

    export_cursor(
        repo_copy,
        repo_copy / "plugins" / "cursor",
        sync_root=True,
    )
    plugin = repo_copy / "plugins" / "cursor" / "codecraft"
    backing = repo_copy / "outside-codecraft"
    plugin.rename(backing)
    plugin.symlink_to(backing, target_is_directory=True)

    messages = _messages(validate_cursor_plugins(repo_copy))
    assert "plugin directory must not be a symlink" in messages
    assert "marketplace source is missing or unsafe" in messages


def test_cursor_validation_rejects_unexpected_generated_skill(
    repo_copy: Path,
) -> None:
    from skills_export.validate_cursor import validate_cursor_plugins

    export_cursor(
        repo_copy,
        repo_copy / "plugins" / "cursor",
        sync_root=True,
    )
    extra = (
        repo_copy
        / "plugins"
        / "cursor"
        / "codecraft"
        / "skills"
        / "unexpected"
    )
    extra.mkdir()
    (extra / "SKILL.md").write_text(
        "---\nname: unexpected\ndescription: Unexpected.\n---\n",
        encoding="utf-8",
    )

    assert "unexpected generated skill 'unexpected'" in _messages(
        validate_cursor_plugins(repo_copy)
    )
