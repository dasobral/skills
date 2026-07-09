from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


TOOL_ROOT = Path(__file__).parents[1]
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    source_root = TOOL_ROOT.parents[1]
    copied_root = tmp_path / "repo"
    copied_root.mkdir()

    for relative in ("core", "adapters", ".cursor-plugin"):
        source = source_root / relative
        if source.exists():
            shutil.copytree(source, copied_root / relative)

    tool_destination = copied_root / "tools" / "skills-export"
    tool_destination.parent.mkdir(parents=True)
    shutil.copytree(TOOL_ROOT / "skills_export", tool_destination / "skills_export")
    shutil.copy2(TOOL_ROOT / "pyproject.toml", tool_destination / "pyproject.toml")
    return copied_root
