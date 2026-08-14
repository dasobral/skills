from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load_installer():
    path = Path(__file__).parents[3] / "bin" / "skills-install"
    loader = SourceFileLoader("skills_install_cli", str(path))
    spec = importlib.util.spec_from_loader("skills_install_cli", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_flat_install_points_at_vercel_cli(capsys) -> None:
    installer = _load_installer()
    sys.argv = ["skills-install", "cursor"]
    assert installer.main() == 2
    err = capsys.readouterr().err
    assert "npx skills add dasobral/skills" in err
    assert "Vercel" in err


def test_claude_plugins_point_at_vercel_cli(capsys) -> None:
    installer = _load_installer()
    sys.argv = ["skills-install", "claude", "--plugins", "--user"]
    assert installer.main() == 2
    assert "npx skills add dasobral/skills" in capsys.readouterr().err
