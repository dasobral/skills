from __future__ import annotations

from pathlib import Path

from skills_export.exporters.codex import export_codex_plugin
from skills_export.exporters.cursor import export_cursor

from test_codex_export import EXISTING_CODEX_AGENTS, _limit_manifest


def _hashes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_codex_export_does_not_change_cursor_plugins(repo_copy: Path) -> None:
    plugin_names = list(EXISTING_CODEX_AGENTS)
    _limit_manifest(repo_copy, plugin_names)
    cursor_output = repo_copy / "plugins" / "cursor"
    export_cursor(
        repo_copy,
        cursor_output,
        plugins=plugin_names,
        sync_root=False,
    )
    before = _hashes(cursor_output)

    for plugin_name in plugin_names:
        export_codex_plugin(
            repo_copy, plugin_name, repo_copy / "plugins" / "codex"
        )

    assert _hashes(cursor_output) == before
