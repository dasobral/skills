"""Claude export shims."""
from __future__ import annotations

from pathlib import Path

from ..assemble import assemble_plugin, export_flat_skills, export_platform
from ..manifest import repo_root


def export_claude_plugin(root, plugin_name, output_dir, *, clean=True):
    return assemble_plugin(Path(root), "claude", plugin_name, Path(output_dir))


def export_claude(root=None, output_dir=None, *, plugins=None, sync_root=False, flat=False, bundles=False):
    if bundles:
        raise ValueError("Claude bundles removed")
    root = Path(root) if root else repo_root()
    out = Path(output_dir) if output_dir else root / "dist" / "claude"
    if sync_root:
        out = root / "dist" / "claude"
    results = export_platform(root, "claude", out, plugins=plugins)
    if flat:
        results.append(export_flat_skills(root, out, platform="claude", plugins=plugins))
    return results
