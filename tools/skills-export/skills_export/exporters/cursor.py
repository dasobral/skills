from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..manifest import (
    copy_skill,
    copy_tree,
    cursor_adapter_dir,
    cursor_plugins_dir,
    load_manifest,
    plugin_skill_names,
    repo_root,
)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _assemble_plugin_json(
    manifest: dict[str, Any], plugin_name: str, adapter: Path
) -> dict[str, Any]:
    plugin_meta = manifest["plugins"][plugin_name]
    base: dict[str, Any] = {
        "name": plugin_name,
        "displayName": plugin_meta["display_name"],
        "version": plugin_meta["version"],
        "description": plugin_meta["description"].strip(),
        "author": manifest.get("author", {"name": "Unknown"}),
        "license": manifest.get("license", "MIT"),
        "keywords": plugin_meta.get("keywords", []),
        "category": plugin_meta.get("category", "developer-tools"),
        "tags": plugin_meta.get("tags", []),
        "skills": "./skills/",
    }

    adapter_json = adapter / "plugin.json"
    if adapter_json.is_file():
        overlay = json.loads(adapter_json.read_text(encoding="utf-8"))
        cursor_cfg = plugin_meta.get("cursor", {})
        for key in ("agents", "rules", "hooks"):
            if cursor_cfg.get(key) and key in overlay:
                base[key] = overlay[key]
            elif key in overlay and overlay[key]:
                base[key] = overlay[key]
    return base


def export_cursor_plugin(
    root: Path,
    plugin_name: str,
    output_dir: Path,
    *,
    clean: bool = True,
) -> Path:
    manifest = load_manifest(root)
    plugin_out = output_dir / plugin_name
    if clean and plugin_out.exists():
        shutil.rmtree(plugin_out)

    adapter = cursor_adapter_dir(root, plugin_name)
    skills_out = plugin_out / "skills"
    skills_out.mkdir(parents=True, exist_ok=True)

    for skill in plugin_skill_names(manifest, plugin_name):
        copy_skill(root, skill, skills_out / skill)

    plugin_json = _assemble_plugin_json(manifest, plugin_name, adapter)
    _write_json(plugin_out / ".cursor-plugin" / "plugin.json", plugin_json)

    for component in ("agents", "hooks", "rules"):
        src = adapter / component
        if src.exists():
            copy_tree(src, plugin_out / component)

    readme = adapter / "README.md"
    if readme.is_file():
        shutil.copy2(readme, plugin_out / "README.md")

    return plugin_out


def _marketplace_plugin_source(plugin_name: str, *, sync_plugins: bool) -> str:
    if sync_plugins:
        return f"plugins/cursor/{plugin_name}"
    return plugin_name


def export_cursor_marketplace(
    root: Path,
    output_dir: Path,
    *,
    sync_plugins: bool = False,
) -> Path:
    """Write marketplace.json.

    When syncing into the repo, always update the root marketplace so Cursor
    discovers plugins under plugins/cursor/. Dist exports keep a local copy.
    """
    manifest = load_manifest(root)
    marketplace_path = root / ".cursor-plugin" / "marketplace.json"

    plugins = []
    for name, meta in manifest["plugins"].items():
        plugins.append(
            {
                "name": name,
                "source": _marketplace_plugin_source(name, sync_plugins=sync_plugins),
                "description": meta["description"].strip(),
                "category": meta.get("category"),
                "tags": meta.get("tags", []),
            }
        )

    if marketplace_path.is_file() and sync_plugins:
        data = json.loads(marketplace_path.read_text(encoding="utf-8"))
        # Preserve owner/metadata; refresh plugin list + sources from manifest
        by_name = {p["name"]: p for p in data.get("plugins", [])}
        refreshed = []
        for entry in plugins:
            prev = by_name.get(entry["name"], {})
            merged = {**prev, **entry}
            # Keep curated marketplace description when present
            if prev.get("description"):
                merged["description"] = prev["description"]
            if prev.get("tags"):
                merged["tags"] = prev["tags"]
            if prev.get("category"):
                merged["category"] = prev["category"]
            refreshed.append(merged)
        # Keep stable order: existing first, then any new plugins
        known = {p["name"] for p in refreshed}
        for prev in data.get("plugins", []):
            if prev["name"] not in known:
                refreshed.append(prev)
        data["plugins"] = refreshed
    elif marketplace_path.is_file() and not sync_plugins:
        data = json.loads(marketplace_path.read_text(encoding="utf-8"))
        # Dist copy: rewrite sources to bare plugin names (relative to dist/cursor)
        for entry in data.get("plugins", []):
            entry["source"] = entry["name"]
    else:
        data = {
            "name": manifest.get("marketplace", {}).get("name", "skills"),
            "metadata": {
                "description": manifest.get("marketplace", {})
                .get("description", "Portable skills marketplace")
                .strip(),
            },
            "plugins": plugins,
        }

    if sync_plugins:
        dest = marketplace_path
    else:
        dest = output_dir / ".cursor-plugin" / "marketplace.json"
    _write_json(dest, data)
    return dest.parent.parent if sync_plugins else output_dir


def export_cursor(
    root: Path | None = None,
    output_dir: Path | None = None,
    *,
    plugins: list[str] | None = None,
    sync_root: bool = False,
) -> list[Path]:
    """Export Cursor plugins.

    sync_root=True writes to plugins/cursor/ and refreshes root marketplace.json.
    Otherwise writes to output_dir or dist/cursor/.
    """
    root = root or repo_root()
    sync_plugins = sync_root
    if output_dir is None:
        output_dir = cursor_plugins_dir(root) if sync_plugins else root / "dist" / "cursor"
    elif sync_plugins:
        # Callers historically passed root; redirect to plugins/cursor/
        if output_dir.resolve() == root.resolve():
            output_dir = cursor_plugins_dir(root)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(root)
    names = plugins or list(manifest["plugins"].keys())
    results = []
    for name in names:
        results.append(export_cursor_plugin(root, name, output_dir))
    export_cursor_marketplace(root, output_dir, sync_plugins=sync_plugins)
    return results
