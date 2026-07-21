from __future__ import annotations

from pathlib import Path

from skills_export.assemble import export_platform
from skills_export.cli import main


def test_export_cursor_assembles_plugin(repo_copy: Path) -> None:
    out = repo_copy / "dist" / "cursor"
    paths = export_platform(repo_copy, "cursor", out, plugins=["career-writer"])
    assert len(paths) == 1
    plugin = out / "career-writer"
    assert (plugin / ".cursor-plugin" / "plugin.json").is_file()
    assert (plugin / "skills" / "career-documents" / "SKILL.md").is_file()


def test_export_claude_assembles_plugin(repo_copy: Path) -> None:
    out = repo_copy / "dist" / "claude"
    export_platform(repo_copy, "claude", out, plugins=["career-writer"])
    assert (out / "career-writer" / ".claude-plugin" / "plugin.json").is_file()
    assert (out / ".claude-plugin" / "marketplace.json").is_file()


def test_export_codex_includes_shared_agent_installer(repo_copy: Path) -> None:
    out = repo_copy / "dist" / "codex"
    export_platform(repo_copy, "codex", out, plugins=["codecraft"])
    assert (
        out / "codecraft" / "skills" / "install-plugin-agents" / "SKILL.md"
    ).is_file()
    assert (out / "codecraft" / "agents" / "code-reviewer.toml").is_file()


def test_cli_validate_and_export(repo_copy: Path) -> None:
    assert main(["--root", str(repo_copy), "validate"]) == 0
    assert main(["--root", str(repo_copy), "export", "claude", "--plugin", "career-writer"]) == 0
    assert (
        repo_copy / "dist" / "claude" / "career-writer" / ".claude-plugin" / "plugin.json"
    ).is_file()


def test_maintain_dry_run(repo_copy: Path, capsys) -> None:
    assert main(["--root", str(repo_copy), "maintain", "--dry-run", "--skip-ingest"]) == 0
    out = capsys.readouterr().out
    assert "would export cursor" in out
    assert "would export claude" in out
    assert "would export codex" in out
