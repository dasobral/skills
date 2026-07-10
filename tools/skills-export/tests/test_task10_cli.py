from __future__ import annotations

from pathlib import Path

from skills_export.cli import main
from skills_export.exporters.codex import export_codex
from skills_export.maintain import maintain


def _files(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_sync_codex_writes_native_plugins_and_marketplace(
    repo_copy: Path,
) -> None:
    cursor_before = _files(repo_copy / "plugins" / "cursor")

    assert main(["--root", str(repo_copy), "sync", "codex"]) == 0

    assert (
        repo_copy
        / "plugins"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    ).is_file()
    assert (repo_copy / ".agents" / "plugins" / "marketplace.json").is_file()
    assert _files(repo_copy / "plugins" / "cursor") == cursor_before


def test_export_codex_writes_only_selected_flat_skills(repo_copy: Path) -> None:
    output = repo_copy / "flat-output"

    assert (
        main(
            [
                "--root",
                str(repo_copy),
                "export",
                "codex",
                "--plugin",
                "career-writer",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    assert {
        path.name for path in (output / "skills").iterdir() if path.is_dir()
    } == {"career-documents"}
    assert not (repo_copy / "plugins" / "codex").exists()
    assert not (repo_copy / ".agents").exists()


def test_validate_codex_checks_generated_output(
    repo_copy: Path,
    capsys,
) -> None:
    assert main(["--root", str(repo_copy), "sync", "codex"]) == 0
    assert main(["--root", str(repo_copy), "validate", "codex"]) == 0
    assert "Codex validation OK" in capsys.readouterr().out

    plugin_json = (
        repo_copy
        / "plugins"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    )
    plugin_json.write_text("{}\n", encoding="utf-8")

    assert main(["--root", str(repo_copy), "validate", "codex"]) == 1
    assert "plugin manifest is missing skills" in capsys.readouterr().err


def test_default_validate_includes_existing_codex_output(
    repo_copy: Path,
) -> None:
    assert main(["--root", str(repo_copy), "sync", "codex"]) == 0
    (
        repo_copy
        / "plugins"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    ).write_text("{}\n", encoding="utf-8")

    assert main(["--root", str(repo_copy), "validate"]) == 1


def test_maintain_dry_run_reports_all_targets_without_writes(
    repo_copy: Path,
) -> None:
    before = _files(repo_copy)

    result = maintain(repo_copy, dry_run=True, skip_ingest=True)

    assert list(result.exports) == ["cursor", "codex", "claude", "codex-flat"]
    assert result.exports["cursor"] == str(repo_copy / "plugins" / "cursor")
    assert result.exports["codex"] == str(repo_copy / "plugins" / "codex")
    assert result.export_counts == {"cursor": 6, "codex": 11}
    assert _files(repo_copy) == before


def test_maintain_dry_run_reports_platform_plugin_counts(
    repo_copy: Path,
    capsys,
) -> None:
    assert main(
        [
            "--root",
            str(repo_copy),
            "maintain",
            "--dry-run",
            "--skip-ingest",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "would export cursor (6 plugins)" in output
    assert "would export codex (11 plugins)" in output


def test_maintain_runs_native_sync_before_flat_exports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import skills_export.maintain as maintain_module

    root = tmp_path / "repo"
    (root / "landing").mkdir(parents=True)
    calls: list[str] = []

    monkeypatch.setattr(
        maintain_module,
        "validate_core",
        lambda _root: calls.append("validate-core") or [],
    )
    monkeypatch.setattr(
        maintain_module,
        "load_manifest",
        lambda _root: {
            "plugins": {
                **{f"cursor-{index}": {"cursor": {}} for index in range(6)},
                **{f"codex-{index}": {} for index in range(5)},
            }
        },
    )
    monkeypatch.setattr(
        maintain_module,
        "export_cursor",
        lambda *_args, **_kwargs: calls.append("sync-cursor") or [],
    )
    monkeypatch.setattr(
        maintain_module,
        "export_codex_plugins",
        lambda *_args, **_kwargs: calls.append("sync-codex") or [],
    )
    monkeypatch.setattr(
        maintain_module,
        "validate_cursor_plugins",
        lambda _root: calls.append("validate-cursor") or [],
    )
    monkeypatch.setattr(
        maintain_module,
        "validate_codex_plugins",
        lambda _root: calls.append("validate-codex") or [],
    )
    monkeypatch.setattr(
        maintain_module,
        "export_claude",
        lambda *_args, **_kwargs: calls.append("export-claude") or [],
    )
    monkeypatch.setattr(
        maintain_module,
        "export_codex",
        lambda *_args, **_kwargs: calls.append("export-codex-flat") or [],
    )

    result = maintain_module.maintain(root, skip_ingest=True)

    assert result.ok()
    assert calls == [
        "validate-core",
        "sync-cursor",
        "sync-codex",
        "validate-cursor",
        "validate-codex",
        "export-claude",
        "export-codex-flat",
    ]


def test_export_codex_api_honors_plugin_filter_for_flat_output(
    repo_copy: Path,
) -> None:
    destination = repo_copy / "dist" / "codex"

    export_codex(
        repo_copy,
        flat_output_dir=destination,
        plugins=["career-writer"],
    )

    assert {
        path.name for path in (destination / "skills").iterdir() if path.is_dir()
    } == {"career-documents"}


def test_export_all_no_flat_keeps_cursor_and_claude_bundles(
    repo_copy: Path,
) -> None:
    output = repo_copy / "all-no-flat"

    assert main(
        [
            "--root",
            str(repo_copy),
            "export",
            "all",
            "--no-flat",
            "--plugin",
            "career-writer",
            "--output",
            str(output),
        ]
    ) == 0

    assert (
        output / "cursor" / "career-writer" / ".cursor-plugin" / "plugin.json"
    ).is_file()
    assert (
        output / "claude" / "bundles" / "career-writer" / "bundle.json"
    ).is_file()
    assert not (output / "claude" / "skills").exists()
    assert not (output / "codex").exists()


def test_export_all_no_bundles_keeps_cursor_and_flat_exports(
    repo_copy: Path,
) -> None:
    output = repo_copy / "all-no-bundles"

    assert main(
        [
            "--root",
            str(repo_copy),
            "export",
            "all",
            "--no-bundles",
            "--plugin",
            "career-writer",
            "--output",
            str(output),
        ]
    ) == 0

    assert (
        output / "cursor" / "career-writer" / ".cursor-plugin" / "plugin.json"
    ).is_file()
    assert not (output / "claude" / "bundles").exists()
    assert (
        output / "claude" / "skills" / "career-documents" / "SKILL.md"
    ).is_file()
    assert (
        output / "codex" / "skills" / "career-documents" / "SKILL.md"
    ).is_file()
