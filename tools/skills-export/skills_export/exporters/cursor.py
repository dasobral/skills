"""Cursor export shims."""
from __future__ import annotations

from pathlib import Path

from ..assemble import assemble_plugin, export_platform
from ..manifest import repo_root


def export_cursor_plugin(root, plugin_name, output_dir, *, clean=True):
    return assemble_plugin(Path(root), "cursor", plugin_name, Path(output_dir))


def export_cursor(root=None, output_dir=None, *, plugins=None, sync_root=False):
    root = Path(root) if root else repo_root()
    out = Path(output_dir) if output_dir else root / "dist" / "cursor"
    if sync_root:
        out = root / "dist" / "cursor"
    return export_platform(root, "cursor", out, plugins=plugins)
