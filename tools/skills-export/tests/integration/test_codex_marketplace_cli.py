from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from skills_export.exporters.codex import export_codex_plugins


pytestmark = pytest.mark.integration


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def _advertised_subcommands(help_text: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(r"(?m)^\s{2,}([a-z][a-z0-9-]*)(?:\s|$)", help_text)
    }


def _require_codex_marketplace_cli(
    *,
    cwd: Path,
    environment: dict[str, str],
) -> tuple[str, set[str]]:
    executable = shutil.which("codex")
    if executable is None:
        pytest.skip("Codex CLI unavailable: executable 'codex' not found on PATH")

    plugin_help = _run(
        [executable, "plugin", "--help"],
        cwd=cwd,
        environment=environment,
    )
    marketplace_help = _run(
        [executable, "plugin", "marketplace", "--help"],
        cwd=cwd,
        environment=environment,
    )
    plugin_text = f"{plugin_help.stdout}\n{plugin_help.stderr}\n"
    marketplace_text = f"{marketplace_help.stdout}\n{marketplace_help.stderr}\n"
    plugin_commands = _advertised_subcommands(plugin_text)
    marketplace_commands = _advertised_subcommands(marketplace_text)
    if (
        plugin_help.returncode != 0
        or marketplace_help.returncode != 0
        or "marketplace" not in plugin_commands
        or not {"add", "list"} <= marketplace_commands
    ):
        pytest.skip(
            "Codex CLI plugin subcommands unavailable: "
            "'codex plugin marketplace add/list' are not supported"
        )

    # Official documentation currently exposes marketplace add/list only.
    # Probe help for future advertised plugin install/list commands without
    # guessing their arguments or claiming that they load local plugins.
    future_commands = plugin_commands & {"install", "list"}
    for command in sorted(future_commands):
        probe = _run(
            [executable, "plugin", command, "--help"],
            cwd=cwd,
            environment=environment,
        )
        assert probe.returncode == 0, probe.stderr
    return executable, future_commands


def _isolated_environment(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    home = tmp_path / "home"
    codex_home = tmp_path / "codex-home"
    home.mkdir()
    codex_home.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "CODEX_HOME": str(codex_home),
            "XDG_CACHE_HOME": str(tmp_path / "xdg-cache"),
            "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
            "XDG_DATA_HOME": str(tmp_path / "xdg-data"),
        }
    )
    return environment, home, codex_home


def test_codex_cli_adds_and_lists_isolated_local_marketplace(
    repo_copy: Path,
    tmp_path: Path,
    record_property,
) -> None:
    environment, _, _ = _isolated_environment(tmp_path)
    executable, future_commands = _require_codex_marketplace_cli(
        cwd=repo_copy,
        environment=environment,
    )
    record_property(
        "advertised_plugin_install_list_commands",
        ",".join(sorted(future_commands)) or "none",
    )
    export_codex_plugins(repo_copy)

    add = _run(
        [executable, "plugin", "marketplace", "add", str(repo_copy)],
        cwd=repo_copy,
        environment=environment,
    )
    assert add.returncode == 0, add.stderr
    listing = _run(
        [executable, "plugin", "marketplace", "list"],
        cwd=repo_copy,
        environment=environment,
    )
    assert listing.returncode == 0, listing.stderr
    inspected = f"{listing.stdout}\n{listing.stderr}"
    assert "dasobral-skills" in inspected
    assert str(repo_copy) in inspected


def test_local_python_checks_manifests_skills_hooks_and_agent_installation(
    repo_copy: Path,
    tmp_path: Path,
) -> None:
    environment, home, codex_home = _isolated_environment(tmp_path)
    export_codex_plugins(repo_copy)

    marketplace = json.loads(
        (repo_copy / ".agents" / "plugins" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(marketplace["plugins"]) == 11
    for entry in marketplace["plugins"]:
        plugin = repo_copy / entry["source"]["path"].removeprefix("./")
        manifest = json.loads(
            (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        assert manifest["name"] == entry["name"]

        skills_root = plugin / manifest["skills"].removeprefix("./")
        skills = list(skills_root.glob("*/SKILL.md"))
        assert skills
        for skill in skills:
            frontmatter = skill.read_text(encoding="utf-8").split("---", 2)[1]
            metadata = yaml.safe_load(frontmatter)
            assert metadata["name"] == skill.parent.name

        if hooks_path := manifest.get("hooks"):
            hook_file = plugin / hooks_path.removeprefix("./")
            hooks = json.loads(hook_file.read_text(encoding="utf-8"))
            assert isinstance(hooks.get("hooks"), dict)
            for event in hooks["hooks"].values():
                for group in event:
                    for hook in group["hooks"]:
                        script = hook["command"].split("${PLUGIN_ROOT}/", 1)[1]
                        assert (plugin / script).is_file()

    project = tmp_path / "project"
    project.mkdir()
    installer = (
        repo_copy
        / "plugins"
        / "codex"
        / "codecraft"
        / "skills"
        / "install-plugin-agents"
        / "scripts"
        / "install_agents.py"
    )
    installed = _run(
        [
            sys.executable,
            str(installer),
            "--scope",
            "project",
            "--project-root",
            str(project),
        ],
        cwd=repo_copy,
        environment=environment,
    )
    assert installed.returncode == 0, installed.stderr
    assert {
        path.name for path in (project / ".codex" / "agents").glob("*.toml")
    } == {"code-reviewer.toml", "convention-analyst.toml"}
    assert not (home / ".codex" / "agents").exists()
    assert codex_home.is_dir()
