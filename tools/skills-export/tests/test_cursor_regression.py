from __future__ import annotations

import hashlib
import json
from pathlib import Path

from skills_export.exporters.codex import export_codex_plugin
from skills_export.exporters.cursor import export_cursor

from test_codex_export import EXISTING_CODEX_AGENTS, _limit_manifest


BASELINE = Path(__file__).parent / "fixtures" / "cursor-origin-main-sha256.json"


def _hashes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(f"{relative}\0{file_hash}\n".encode())
    return digest.hexdigest()


def test_cursor_export_matches_explicit_origin_main_baseline(repo_copy: Path) -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    output = repo_copy / "plugins" / "cursor"

    assert baseline["source"] == {
        "ref": "origin/main",
        "commit": "19d37c87912696474e7f897c5a83dc992bc0825c",
    }
    exported = export_cursor(repo_copy, output, sync_root=False)

    expected_plugins = baseline["plugins"]
    assert len(exported) == 6
    assert sorted(path.name for path in exported) == sorted(expected_plugins)
    generated_plugins = [
        path.name
        for path in output.iterdir()
        if path.is_dir() and (path / ".cursor-plugin" / "plugin.json").is_file()
    ]
    assert sorted(generated_plugins) == sorted(expected_plugins)
    assert set(baseline["allowlistedSkillChanges"]) == {
        "agent-platform/skills/agent-ste/",
        "agent-platform/skills/create-agent/",
        "codecraft/skills/write-conformant-code/",
        "cpp-qkd-toolkit/skills/cpp-engineer/",
    }
    assert all(baseline["allowlistedSkillChanges"].values())

    actual_files = {
        relative: hashlib.sha256((output / relative).read_bytes()).hexdigest()
        for relative in baseline["files"]
    }
    assert actual_files == baseline["files"]
    actual_skill_trees = {
        relative: _tree_hash(output / relative)
        for relative in baseline["skillTrees"]
    }
    assert actual_skill_trees == baseline["skillTrees"]

    protected = set(baseline["files"])
    allowlisted = tuple(baseline["allowlistedSkillChanges"])
    for path in output.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(output).as_posix()
        if relative.startswith(".cursor-plugin/"):
            continue
        if any(relative.startswith(prefix) for prefix in allowlisted):
            continue
        if "/skills/" not in relative:
            assert relative in protected


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
