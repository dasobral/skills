from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest

import skills_export.agent_installer as installer
from skills_export.agent_installer import install_agent_templates
from skills_export.exporters.codex import export_codex_plugin
from test_codex_export import _write_codex_overlay


def _source(tmp_path: Path, *, two: bool = False) -> Path:
    plugin = tmp_path / "plugin"
    source = plugin / "agents"
    source.mkdir(parents=True)
    (plugin / ".codex-plugin").mkdir()
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        '{"name": "test-plugin", "version": "1.2.3"}\n',
        encoding="utf-8",
    )
    (source / "reviewer.toml").write_text(
        'name = "reviewer"\n'
        'description = "Reviews code."\n'
        'developer_instructions = "Review carefully."\n',
        encoding="utf-8",
    )
    if two:
        (source / "analyst.toml").write_text(
            'name = "analyst"\n'
            'description = "Analyzes code."\n'
            'developer_instructions = "Analyze carefully."\n',
            encoding="utf-8",
        )
    return source


def _named_source(
    root: Path,
    plugin_name: str,
    agent_name: str,
) -> Path:
    plugin = root / plugin_name
    source = plugin / "agents"
    source.mkdir(parents=True)
    (plugin / ".codex-plugin").mkdir()
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": plugin_name, "version": "1.0.0"}) + "\n",
        encoding="utf-8",
    )
    (source / f"{agent_name}.toml").write_text(
        f'name = "{agent_name}"\n'
        f'description = "{agent_name} agent."\n'
        'developer_instructions = "Work carefully."\n',
        encoding="utf-8",
    )
    return source


def test_installs_project_scoped_agents(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    result = install_agent_templates(
        source, scope="project", project_root=project
    )

    assert result.destination == project / ".codex" / "agents"
    assert [(action.path.name, action.status) for action in result.actions] == [
        ("reviewer.toml", "added")
    ]
    assert (result.destination / "reviewer.toml").is_file()


def test_installs_user_scoped_agents(tmp_path: Path) -> None:
    source = _source(tmp_path)
    home = tmp_path / "home"
    home.mkdir()

    result = install_agent_templates(source, scope="user", home=home)

    assert result.destination == home / ".codex" / "agents"
    assert (result.destination / "reviewer.toml").is_file()


def test_dry_run_previews_without_writing(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    result = install_agent_templates(
        source,
        scope="project",
        project_root=project,
        dry_run=True,
    )

    assert [action.status for action in result.actions] == ["added"]
    assert not result.destination.exists()
    assert not result.ledger.exists()


def test_dry_run_in_existing_destination_does_not_create_lock(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    destination = project / ".codex" / "agents"
    destination.mkdir(parents=True)

    install_agent_templates(
        source,
        scope="project",
        project_root=project,
        dry_run=True,
    )

    assert list(destination.iterdir()) == []


def test_identical_reinstall_is_unchanged(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    install_agent_templates(source, scope="project", project_root=project)

    result = install_agent_templates(
        source, scope="project", project_root=project
    )

    assert [action.status for action in result.actions] == ["unchanged"]


def test_conflict_refuses_complete_batch(tmp_path: Path) -> None:
    source = _source(tmp_path, two=True)
    project = tmp_path / "project"
    destination = project / ".codex" / "agents"
    destination.mkdir(parents=True)
    (destination / "reviewer.toml").write_text("different\n", encoding="utf-8")

    result = install_agent_templates(
        source, scope="project", project_root=project
    )

    assert {action.status for action in result.actions} == {"added", "conflict"}
    assert not (destination / "analyst.toml").exists()
    assert not result.ledger.exists()
    assert (destination / "reviewer.toml").read_text(encoding="utf-8") == (
        "different\n"
    )


def test_new_files_are_replaced_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    replacements: list[tuple[tuple[object, ...], dict[str, object]]] = []
    real_replace = os.replace

    def record_replace(*args: object, **kwargs: object) -> None:
        replacements.append((args, kwargs))
        real_replace(*args, **kwargs)

    monkeypatch.setattr(installer.os, "replace", record_replace)

    install_agent_templates(source, scope="project", project_root=project)

    target_sources = [
        (args[0], kwargs)
        for args, kwargs in replacements
        if str(args[1]).endswith("reviewer.toml")
    ]
    assert len(target_sources) == 1
    assert target_sources[0][0] == "reviewer.toml"
    assert target_sources[0][1]["src_dir_fd"] != target_sources[0][1]["dst_dir_fd"]


def test_invalid_source_aborts_before_any_write(tmp_path: Path) -> None:
    source = _source(tmp_path, two=True)
    (source / "reviewer.toml").write_text("name = [", encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ValueError, match="invalid agent TOML"):
        install_agent_templates(
            source, scope="project", project_root=project
        )

    assert not (project / ".codex").exists()


def test_source_path_rejects_dot_dot(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    source_with_traversal = source / ".." / "agents"

    with pytest.raises(ValueError, match=r"\.\."):
        install_agent_templates(
            source_with_traversal,
            scope="project",
            project_root=project,
        )


def test_destination_symlink_escape_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (project / ".codex").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink|escapes"):
        install_agent_templates(
            source, scope="project", project_root=project
        )

    assert not (outside / "agents").exists()


def test_hash_ledger_records_installed_templates(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    result = install_agent_templates(
        source, scope="project", project_root=project
    )

    assert result.ledger.name == ".plugin-agent-install.test-plugin.json"
    ledger = json.loads(result.ledger.read_text(encoding="utf-8"))
    expected_hash = hashlib.sha256(
        (source / "reviewer.toml").read_bytes()
    ).hexdigest()
    assert ledger == {
        "plugin": "test-plugin",
        "version": "1.2.3",
        "files": [
            {
                "file": "reviewer.toml",
                "sha256": expected_hash,
            }
        ],
    }


def test_shared_setup_skill_requires_preview_and_confirmation() -> None:
    root = Path(__file__).parents[3]
    skill = (
        root
        / "adapters"
        / "codex"
        / "_shared"
        / "skills"
        / "install-plugin-agents"
    )
    text = (skill / "SKILL.md").read_text(encoding="utf-8")

    assert text.startswith("---\nname: install-plugin-agents\n")
    for required in (
        "project or user",
        "--dry-run",
        "additions",
        "conflicts",
        "explicit confirmation",
        "new Codex session",
    ):
        assert required in text
    assert (skill / "scripts" / "install_agents.py").is_file()


def test_generated_setup_script_installs_agents_end_to_end(
    repo_copy: Path,
) -> None:
    _write_codex_overlay(repo_copy)
    plugin = export_codex_plugin(
        repo_copy, "codecraft", repo_copy / "plugins" / "codex"
    )
    project = repo_copy / "project"
    project.mkdir()
    script = (
        plugin
        / "skills"
        / "install-plugin-agents"
        / "scripts"
        / "install_agents.py"
    )
    command = [
        sys.executable,
        str(script),
        "--scope",
        "project",
        "--project-root",
        str(project),
    ]

    preview = subprocess.run(
        [*command, "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "added:" in preview.stdout
    assert not (project / ".codex").exists()

    subprocess.run(command, check=True, capture_output=True, text=True)
    assert (project / ".codex" / "agents" / "code-reviewer.toml").is_file()


def test_rejects_internal_source_template_symlink(tmp_path: Path) -> None:
    source = _source(tmp_path)
    original = source / "reviewer.toml"
    alias = source / "alias.toml"
    alias.symlink_to(original)
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ValueError, match="symlink"):
        install_agent_templates(
            source, scope="project", project_root=project
        )


def test_rejects_destination_parent_symlink_even_when_internal(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    internal = project / "internal"
    project.mkdir()
    internal.mkdir()
    (project / ".codex").symlink_to(internal, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        install_agent_templates(
            source, scope="project", project_root=project
        )


def test_batch_failure_rolls_back_all_agent_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, two=True)
    project = tmp_path / "project"
    project.mkdir()
    real_replace = os.replace
    template_replacements = 0

    def fail_second_template(*args: object, **kwargs: object) -> None:
        nonlocal template_replacements
        destination = Path(str(args[1]))
        if destination.suffix == ".toml":
            template_replacements += 1
            if template_replacements == 2:
                raise OSError("injected commit failure")
        real_replace(*args, **kwargs)

    monkeypatch.setattr(installer.os, "replace", fail_second_template)

    with pytest.raises(OSError, match="injected commit failure"):
        install_agent_templates(
            source, scope="project", project_root=project
        )

    destination = project / ".codex" / "agents"
    assert not list(destination.glob("*.toml"))
    assert not list(destination.glob(".plugin-agent-install.*.json"))
    assert not list(destination.glob(".*.stage-*"))


def test_all_templates_are_staged_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, two=True)
    project = tmp_path / "project"
    project.mkdir()
    real_replace = os.replace
    observed_stage_files: set[str] = set()

    def inspect_first_template(*args: object, **kwargs: object) -> None:
        if Path(str(args[1])).suffix == ".toml" and not observed_stage_files:
            source_fd = kwargs.get("src_dir_fd")
            assert isinstance(source_fd, int)
            observed_stage_files.update(os.listdir(source_fd))
        real_replace(*args, **kwargs)

    monkeypatch.setattr(installer.os, "replace", inspect_first_template)

    install_agent_templates(source, scope="project", project_root=project)

    assert observed_stage_files == {"analyst.toml", "reviewer.toml"}


def test_plugin_ledgers_do_not_overwrite_each_other(tmp_path: Path) -> None:
    first = _named_source(tmp_path / "sources", "first-plugin", "first-agent")
    second = _named_source(tmp_path / "sources", "second-plugin", "second-agent")
    project = tmp_path / "project"
    project.mkdir()

    first_result = install_agent_templates(
        first, scope="project", project_root=project
    )
    first_ledger = first_result.ledger.read_bytes()
    second_result = install_agent_templates(
        second, scope="project", project_root=project
    )

    assert first_result.ledger != second_result.ledger
    assert first_result.ledger.read_bytes() == first_ledger
    assert second_result.ledger.is_file()


def test_pending_journal_is_recovered_before_retry(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    destination = project / ".codex" / "agents"
    destination.mkdir(parents=True)
    content = (source / "reviewer.toml").read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    (destination / "reviewer.toml").write_bytes(content)
    stage = destination / ".test-plugin.stage-interrupted"
    stage.mkdir()
    journal = destination / ".plugin-agent-install.test-plugin.journal.json"
    journal.write_text(
        json.dumps(
            {
                "plugin": "test-plugin",
                "version": "1.2.3",
                "stage": stage.name,
                "files": [{"file": "reviewer.toml", "sha256": digest}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = install_agent_templates(
        source, scope="project", project_root=project
    )

    assert [action.status for action in result.actions] == ["added"]
    assert (destination / "reviewer.toml").is_file()
    assert not journal.exists()
    assert not stage.exists()


def test_failure_after_ledger_replace_restores_previous_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    first = install_agent_templates(
        source,
        scope="project",
        project_root=project,
    )
    previous_ledger = first.ledger.read_bytes()
    (source / "analyst.toml").write_text(
        'name = "analyst"\n'
        'description = "Analyzes code."\n'
        'developer_instructions = "Analyze carefully."\n',
        encoding="utf-8",
    )
    real_atomic_write = installer._atomic_write
    failed = False

    def fail_after_ledger_replace(
        path: Path,
        content: bytes,
        directory_fd: int | None = None,
    ) -> None:
        nonlocal failed
        real_atomic_write(path, content, directory_fd)
        if path == first.ledger and not failed:
            failed = True
            raise OSError("injected post-ledger failure")

    monkeypatch.setattr(installer, "_atomic_write", fail_after_ledger_replace)

    with pytest.raises(OSError, match="post-ledger"):
        install_agent_templates(
            source,
            scope="project",
            project_root=project,
        )

    assert first.ledger.read_bytes() == previous_ledger
    assert (first.destination / "reviewer.toml").is_file()
    assert not (first.destination / "analyst.toml").exists()
    assert not list(first.destination.glob("*.journal.json"))
    assert not list(first.destination.glob(".*.stage-*"))


def test_rejects_symlinked_source_ancestor(tmp_path: Path) -> None:
    real_sources = tmp_path / "real-sources"
    source = _named_source(real_sources, "test-plugin", "reviewer")
    linked_sources = tmp_path / "sources"
    linked_sources.symlink_to(real_sources, target_is_directory=True)
    linked_source = linked_sources / source.relative_to(real_sources)
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ValueError, match="source ancestor.*symlink"):
        install_agent_templates(
            linked_source,
            scope="project",
            project_root=project,
        )


def test_rejects_symlinked_install_lock(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    destination = project / ".codex" / "agents"
    destination.mkdir(parents=True)
    outside = tmp_path / "outside-lock"
    outside.write_text("outside", encoding="utf-8")
    lock = destination / ".plugin-agent-install.lock"
    lock.symlink_to(outside)

    with pytest.raises(ValueError, match="lock.*symlink"):
        install_agent_templates(
            source,
            scope="project",
            project_root=project,
        )

    assert outside.read_text(encoding="utf-8") == "outside"


def test_concurrent_plugins_with_same_agent_filename_are_serialized(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    first = _named_source(sources, "first-plugin", "reviewer")
    second = _named_source(sources, "second-plugin", "reviewer")
    (second / "reviewer.toml").write_text(
        'name = "reviewer"\n'
        'description = "Second reviewer."\n'
        'developer_instructions = "Use the second policy."\n',
        encoding="utf-8",
    )
    project = tmp_path / "project"
    project.mkdir()
    marker = tmp_path / "first-staged"
    slow_script = """
import pathlib
import sys
import time
import skills_export.agent_installer as ai

real = ai._stage_template
marker = pathlib.Path(sys.argv[1])

def slow(stage, template, *args, **kwargs):
    marker.write_text("ready", encoding="utf-8")
    time.sleep(0.75)
    return real(stage, template, *args, **kwargs)

ai._stage_template = slow
raise SystemExit(ai.main(sys.argv[2:]))
"""
    first_process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            slow_script,
            str(marker),
            str(first),
            "--scope",
            "project",
            "--project-root",
            str(project),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 5
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker.exists(), first_process.communicate(timeout=5)

    second_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "skills_export.agent_installer",
            str(second),
            "--scope",
            "project",
            "--project-root",
            str(project),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    first_stdout, first_stderr = first_process.communicate(timeout=10)

    assert sorted([first_process.returncode, second_result.returncode]) == [0, 2], (
        first_stdout,
        first_stderr,
        second_result.stdout,
        second_result.stderr,
    )
    installed = project / ".codex" / "agents" / "reviewer.toml"
    assert installed.read_bytes() == (first / "reviewer.toml").read_bytes()


def test_install_uses_descriptor_anchored_replacements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    real_replace = os.replace
    replacements: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record_replace(*args: object, **kwargs: object) -> None:
        replacements.append((args, kwargs))
        real_replace(*args, **kwargs)

    monkeypatch.setattr(installer.os, "replace", record_replace)

    install_agent_templates(source, scope="project", project_root=project)

    assert any(
        str(args[1]).endswith("reviewer.toml")
        and kwargs.get("src_dir_fd") is not None
        and kwargs.get("dst_dir_fd") is not None
        for args, kwargs in replacements
    )
    assert any(
        str(args[1]).endswith(".plugin-agent-install.test-plugin.json")
        and kwargs.get("dst_dir_fd") is not None
        for args, kwargs in replacements
    )


def test_windows_lock_fallback_uses_destination_wide_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "agents"
    destination.mkdir()
    calls: list[int] = []
    fake_msvcrt = types.SimpleNamespace(
        LK_LOCK=1,
        LK_UNLCK=2,
        locking=lambda _fd, mode, _size: calls.append(mode),
    )
    monkeypatch.setattr(installer, "fcntl", None)
    monkeypatch.setattr(installer, "msvcrt", fake_msvcrt, raising=False)
    monkeypatch.setattr(installer, "ANCHOR_SUPPORTED", False)

    with installer._installation_lock(destination):
        assert (destination / ".plugin-agent-install.lock").is_file()

    assert calls == [fake_msvcrt.LK_LOCK, fake_msvcrt.LK_UNLCK]
