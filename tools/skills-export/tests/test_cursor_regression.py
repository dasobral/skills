from __future__ import annotations

from pathlib import Path

from skills_export.exporters.codex import export_codex_plugin
from skills_export.exporters.cursor import export_cursor

from test_codex_export import _write_codex_overlay


def _hashes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_codex_export_does_not_change_cursor_plugins(repo_copy: Path) -> None:
    cursor_output = repo_copy / "plugins" / "cursor"
    export_cursor(
        repo_copy,
        cursor_output,
        plugins=["codecraft"],
        sync_root=False,
    )
    before = _hashes(cursor_output)
    _write_codex_overlay(repo_copy)

    export_codex_plugin(
        repo_copy, "codecraft", repo_copy / "plugins" / "codex"
    )

    assert _hashes(cursor_output) == before
