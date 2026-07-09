from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..manifest import (
    copy_skill,
    copy_tree,
    cursor_adapter_dir,
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


def export_cursor_marketplace(root: Path, output_dir: Path) -> Path:
    manifest = load_manifest(root)
    marketplace_path = root / ".cursor-plugin" / "marketplace.json"
    dest = output_dir / ".cursor-plugin" / "marketplace.json"
    if marketplace_path.is_file():
        if marketplace_path.resolve() != dest.resolve():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(marketplace_path, dest)
    else:
        plugins = []
        for name, meta in manifest["plugins"].items():
            plugins.append(
                {
                    "name": name,
                    "source": name,
                    "description": meta["description"].strip(),
                    "category": meta.get("category"),
                    "tags": meta.get("tags", []),
                }
            )
        data = {
            "name": manifest.get("marketplace", {}).get("name", "skills"),
            "metadata": {
                "description": manifest.get("marketplace", {}).get(
                    "description", "Portable skills marketplace"
                ).strip(),
            },
            "plugins": plugins,
        }
        _write_json(output_dir / ".cursor-plugin" / "marketplace.json", data)
    return output_dir


def export_cursor(
    root: Path | None = None,
    output_dir: Path | None = None,
    *,
    plugins: list[str] | None = None,
    sync_root: bool = False,
) -> list[Path]:
    root = root or repo_root()
    output_dir = output_dir or (root if sync_root else root / "dist" / "cursor")
    manifest = load_manifest(root)
    names = plugins or list(manifest["plugins"].keys())
    results = []
    for name in names:
        results.append(export_cursor_plugin(root, name, output_dir))
    export_cursor_marketplace(root, output_dir)
    return results
