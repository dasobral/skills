from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path

from skills_export.exporters.codex import export_codex_plugins

from test_codex_export import _limit_manifest


INSTALLER = Path(__file__).parents[3] / "bin" / "skills-install"


def _run_installer(
    repo: Path,
    *args: str,
    home: Path,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(INSTALLER), *args],
        cwd=cwd or repo,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _generate_one_plugin(repo: Path) -> None:
    _limit_manifest(repo, ["codecraft"])
    export_codex_plugins(repo)


def test_codex_project_plugin_install_preserves_native_layout_without_agents(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    project = repo_copy / "example-project"
    project.mkdir()

    completed = _run_installer(
        repo_copy,
        "codex",
        "--plugins",
        "--project",
        home=tmp_path / "home",
        cwd=project,
    )

    assert completed.returncode == 0, completed.stderr
    assert (
        project
        / "plugins"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    ).is_file()
    assert (project / ".agents" / "plugins" / "marketplace.json").is_file()
    assert not (project / ".codex" / "agents").exists()


def test_codex_user_plugin_install_preserves_native_layout_without_agents(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    home = tmp_path / "home"

    completed = _run_installer(
        repo_copy,
        "codex",
        "--plugins",
        "--user",
        home=home,
    )

    assert completed.returncode == 0, completed.stderr
    assert (
        home
        / "plugins"
        / "codex"
        / "codecraft"
        / ".codex-plugin"
        / "plugin.json"
    ).is_file()
    assert (home / ".agents" / "plugins" / "marketplace.json").is_file()
    assert not (home / ".codex" / "agents").exists()


def test_codex_flat_install_does_not_install_native_plugins(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    flat_skill = repo_copy / "dist" / "codex" / "skills" / "example"
    flat_skill.mkdir(parents=True)
    (flat_skill / "SKILL.md").write_text(
        "---\nname: example\ndescription: Example.\n---\n",
        encoding="utf-8",
    )
    project = repo_copy / "flat-project"
    project.mkdir()

    completed = _run_installer(
        repo_copy,
        "codex",
        "--project",
        home=tmp_path / "home",
        cwd=project,
    )

    assert completed.returncode == 0, completed.stderr
    assert (project / ".agents" / "skills" / "example" / "SKILL.md").is_file()
    assert not (project / "plugins" / "codex").exists()
    assert not (project / ".agents" / "plugins").exists()


def test_codex_plugin_install_rejects_symlinked_destination(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    project = repo_copy / "unsafe-project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "plugins").symlink_to(outside, target_is_directory=True)

    completed = _run_installer(
        repo_copy,
        "codex",
        "--plugins",
        "--project",
        home=tmp_path / "home",
        cwd=project,
    )

    assert completed.returncode != 0
    assert "symlink" in completed.stderr.lower()
    assert not list(outside.iterdir())


def test_codex_plugin_install_rejects_symlinked_source_container(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    source = repo_copy / "plugins" / "codex"
    backing = repo_copy / "real-codex-plugins"
    source.rename(backing)
    source.symlink_to(backing, target_is_directory=True)
    project = repo_copy / "source-symlink-project"
    project.mkdir()

    completed = _run_installer(
        repo_copy,
        "codex",
        "--plugins",
        "--project",
        home=tmp_path / "home",
        cwd=project,
    )

    assert completed.returncode != 0
    assert "symlink" in completed.stderr.lower()
    assert not (project / "plugins").exists()


def test_codex_plugin_install_preflights_marketplace_destination(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    project = repo_copy / "marketplace-directory-project"
    marketplace = project / ".agents" / "plugins" / "marketplace.json"
    marketplace.mkdir(parents=True)

    completed = _run_installer(
        repo_copy,
        "codex",
        "--plugins",
        "--project",
        home=tmp_path / "home",
        cwd=project,
    )

    assert completed.returncode != 0
    assert "marketplace destination is not a file" in completed.stderr.lower()
    assert not (project / "plugins").exists()


def test_project_plugin_install_merges_marketplace_without_reordering(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    project = repo_copy / "merge-project"
    marketplace = project / ".agents" / "plugins" / "marketplace.json"
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(
        json.dumps(
            {
                "name": "personal-marketplace",
                "owner": {"team": "research"},
                "plugins": [
                    {"name": "before", "source": {"source": "git", "url": "one"}},
                    {
                        "name": "codecraft",
                        "source": {
                            "source": "local",
                            "path": "./plugins/codex/codecraft",
                        },
                        "custom": "preserve-me",
                    },
                    {"name": "after", "source": {"source": "git", "url": "two"}},
                ],
            }
        ),
        encoding="utf-8",
    )

    completed = _run_installer(
        repo_copy,
        "codex",
        "--plugins",
        "--project",
        home=tmp_path / "home",
        cwd=project,
    )

    assert completed.returncode == 0, completed.stderr
    merged = json.loads(marketplace.read_text(encoding="utf-8"))
    assert merged["name"] == "personal-marketplace"
    assert merged["owner"] == {"team": "research"}
    assert [entry["name"] for entry in merged["plugins"]] == [
        "before",
        "codecraft",
        "after",
    ]
    assert merged["plugins"][1]["custom"] == "preserve-me"
    assert merged["plugins"][1]["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }


def test_user_plugin_install_refuses_conflicting_marketplace_source(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    home = tmp_path / "home"
    marketplace = home / ".agents" / "plugins" / "marketplace.json"
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(
        json.dumps(
            {
                "name": "personal",
                "plugins": [
                    {
                        "name": "codecraft",
                        "source": {
                            "source": "local",
                            "path": "./other/codecraft",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    completed = _run_installer(
        repo_copy,
        "codex",
        "--plugins",
        "--user",
        home=home,
    )

    assert completed.returncode != 0
    assert "conflicting marketplace source" in completed.stderr.lower()
    assert not (home / "plugins").exists()
    assert json.loads(marketplace.read_text(encoding="utf-8"))["plugins"][0][
        "source"
    ]["path"] == "./other/codecraft"


def test_user_plugin_install_explicitly_replaces_conflicting_source_safely(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    _generate_one_plugin(repo_copy)
    home = tmp_path / "home"
    marketplace = home / ".agents" / "plugins" / "marketplace.json"
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(
        json.dumps(
            {
                "name": "personal",
                "custom": {"keep": True},
                "plugins": [
                    {"name": "other", "source": {"source": "git", "url": "repo"}},
                    {
                        "name": "codecraft",
                        "source": {
                            "source": "local",
                            "path": "./other/codecraft",
                        },
                        "note": "retained",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    completed = _run_installer(
        repo_copy,
        "codex",
        "--plugins",
        "--user",
        "--replace-conflicts",
        home=home,
    )

    assert completed.returncode == 0, completed.stderr
    merged = json.loads(marketplace.read_text(encoding="utf-8"))
    assert merged["custom"] == {"keep": True}
    assert [entry["name"] for entry in merged["plugins"]] == [
        "other",
        "codecraft",
    ]
    assert merged["plugins"][1]["source"] == {
        "source": "local",
        "path": "./plugins/codex/codecraft",
    }
    assert merged["plugins"][1]["note"] == "retained"
    assert (home / "plugins" / "codex" / "codecraft").is_dir()


def test_claude_rejects_native_plugin_mode(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    completed = _run_installer(
        repo_copy,
        "claude",
        "--plugins",
        "--user",
        home=tmp_path / "home",
    )

    assert completed.returncode == 2
    assert "--plugins is only supported for cursor and codex" in completed.stderr


def test_cursor_rejects_codex_conflict_replacement_policy(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    completed = _run_installer(
        repo_copy,
        "cursor",
        "--plugins",
        "--replace-conflicts",
        "--user",
        home=tmp_path / "home",
    )

    assert completed.returncode == 2
    assert "--replace-conflicts requires codex --plugins" in completed.stderr


def test_replacement_policy_requires_codex_plugin_mode(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    completed = _run_installer(
        repo_copy,
        "codex",
        "--replace-conflicts",
        "--user",
        home=tmp_path / "home",
    )

    assert completed.returncode == 2
    assert "--replace-conflicts requires codex --plugins" in completed.stderr
