"""Thin compatibility shims — use skills_export.assemble instead."""
from __future__ import annotations

from pathlib import Path

from ..assemble import assemble_plugin, export_flat_skills, export_platform


def export_cursor(root=None, output_dir=None, *, plugins=None, sync_root=False):
    root = Path(root) if root else None
    out = output_dir
    if sync_root and root is not None:
        out = Path(root) / "dist" / "cursor"
    return export_platform(root, "cursor", out, plugins=plugins)


def export_claude(root=None, output_dir=None, *, plugins=None, sync_root=False, flat=False, bundles=False):
    if bundles:
        raise ValueError("Claude bundles removed; use native plugins via export_platform")
    root = Path(root) if root else None
    out = output_dir
    if sync_root and root is not None:
        out = Path(root) / "dist" / "claude"
    results = export_platform(root, "claude", out, plugins=plugins)
    if flat:
        results.append(export_flat_skills(root, out, platform="claude", plugins=plugins))
    return results


def export_codex(root=None, output_dir=None, *, flat_output_dir=None, plugins=None, flat=True, native=False, **kwargs):
    if kwargs.get("bundles") is not None:
        raise ValueError("legacy Codex bundles were removed")
    root = Path(root) if root else None
    dest = flat_output_dir or output_dir
    if flat:
        return [export_flat_skills(root, dest, platform="codex", plugins=plugins)]
    return export_platform(root, "codex", dest, plugins=plugins)


def export_codex_plugins(root=None, output_root=None, *, plugins=None, clean=True):
    return export_platform(root, "codex", output_root, plugins=plugins)


def export_cursor_plugin(root, plugin_name, output_dir, *, clean=True):
    return assemble_plugin(Path(root), "cursor", plugin_name, Path(output_dir))


def export_claude_plugin(root, plugin_name, output_dir, *, clean=True):
    return assemble_plugin(Path(root), "claude", plugin_name, Path(output_dir))


def export_codex_plugin(root, plugin_name, output_root, *, clean=True):
    return assemble_plugin(Path(root), "codex", plugin_name, Path(output_root))
