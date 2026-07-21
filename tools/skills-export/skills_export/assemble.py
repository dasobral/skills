"""Assemble platform plugins from core skills + adapter scaffolding."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .manifest import (
    adapter_dir,
    copy_skill,
    copy_tree,
    load_manifest,
    platform_plugin_names,
    plugin_skill_names,
    plugins_dir,
    repo_root,
)

PLATFORMS = ("cursor", "claude", "codex")

_MANIFEST_DIR = {
    "cursor": ".cursor-plugin",
    "claude": ".claude-plugin",
    "codex": ".codex-plugin",
}

_COMPONENTS = {
    "cursor": ("agents", "hooks", "rules"),
    "claude": ("agents", "hooks", "commands"),
    "codex": ("agents", "hooks"),
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _plugin_manifest(
    platform: str,
    plugin_name: str,
    meta: dict[str, Any],
    root_manifest: dict[str, Any],
    adapter: Path,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "name": plugin_name,
        "version": meta["version"],
        "description": meta["description"].strip(),
        "author": root_manifest.get("author", {"name": "Unknown"}),
        "license": root_manifest.get("license", "MIT"),
        "keywords": meta.get("keywords", []),
        "skills": "./skills/",
    }
    if meta.get("display_name"):
        if platform == "cursor":
            base["displayName"] = meta["display_name"]
        elif platform == "claude":
            base["displayName"] = meta["display_name"]

    overlay_path = adapter / "plugin.json"
    if not overlay_path.is_file() and platform == "codex":
        overlay_path = adapter / ".codex-plugin" / "plugin.json"
    if overlay_path.is_file():
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        platform_cfg = meta.get(platform, {})
        for key in ("agents", "rules", "hooks", "commands", "mcpServers", "apps"):
            if key in overlay and (platform_cfg.get(key, True) or key in ("mcpServers", "apps")):
                if platform_cfg.get(key) is False:
                    continue
                base[key] = overlay[key]
        for key in ("interface", "homepage", "repository", "category", "tags"):
            if key in overlay:
                base[key] = overlay[key]

    # Cursor/Claude adapters store component paths in overlay; ensure defaults when dirs exist
    for component in _COMPONENTS[platform]:
        if (adapter / component).exists() and component not in base:
            if component == "hooks":
                base["hooks"] = "./hooks/hooks.json"
            else:
                base[component] = f"./{component}/"

    if platform == "codex" and (adapter / "hooks").exists() and meta.get("codex", {}).get("hooks"):
        base["hooks"] = "./hooks/hooks.json"

    return base


def assemble_plugin(
    root: Path,
    platform: str,
    plugin_name: str,
    output_dir: Path,
) -> Path:
    manifest = load_manifest(root)
    meta = manifest["plugins"][plugin_name]
    adapter = adapter_dir(root, platform, plugin_name)
    plugin_out = output_dir / plugin_name
    if plugin_out.exists():
        shutil.rmtree(plugin_out)

    skills_out = plugin_out / "skills"
    skills_out.mkdir(parents=True, exist_ok=True)
    for skill in plugin_skill_names(manifest, plugin_name):
        copy_skill(root, skill, skills_out / skill)

    # Codex adapter-only skills (runtime helpers)
    adapter_skills = adapter / "skills"
    if adapter_skills.is_dir():
        for skill_dir in adapter_skills.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").is_file():
                copy_tree(skill_dir, skills_out / skill_dir.name)

    # Shared Codex install-plugin-agents skill
    if platform == "codex":
        shared = root / "adapters" / "codex" / "_shared" / "skills" / "install-plugin-agents"
        if shared.is_dir():
            copy_tree(shared, skills_out / "install-plugin-agents")
            installer = root / "tools" / "skills-export" / "skills_export" / "agent_installer.py"
            if installer.is_file():
                shutil.copy2(
                    installer,
                    skills_out / "install-plugin-agents" / "scripts" / "agent_installer.py",
                )

    plugin_json = _plugin_manifest(platform, plugin_name, meta, manifest, adapter)
    _write_json(plugin_out / _MANIFEST_DIR[platform] / "plugin.json", plugin_json)

    for component in _COMPONENTS[platform]:
        src = adapter / component
        if src.exists():
            copy_tree(src, plugin_out / component)

    for extra in (".mcp.json",):
        src = adapter / extra
        if src.is_file():
            shutil.copy2(src, plugin_out / extra)

    # Codex may store overlay files beside .codex-plugin
    if platform == "codex":
        for path in adapter.iterdir():
            if path.name in {".codex-plugin", "plugin.json", "skills", "agents", "hooks", "README.md"}:
                continue
            if path.is_file():
                shutil.copy2(path, plugin_out / path.name)
            elif path.is_dir():
                copy_tree(path, plugin_out / path.name)

    readme = adapter / "README.md"
    if readme.is_file():
        shutil.copy2(readme, plugin_out / "README.md")
    else:
        skills = plugin_skill_names(manifest, plugin_name)
        (plugin_out / "README.md").write_text(
            f"# {meta['display_name']}\n\nSkills: {', '.join(skills)}\n",
            encoding="utf-8",
        )
    return plugin_out


def _marketplace_entries(
    root: Path,
    platform: str,
    names: list[str],
    *,
    source_prefix: str,
) -> dict[str, Any]:
    manifest = load_manifest(root)
    author = manifest.get("author", {"name": "Unknown"})
    entries = []
    for name in names:
        meta = manifest["plugins"][name]
        if platform == "codex":
            entries.append(
                {
                    "name": name,
                    "source": {"source": "local", "path": f"{source_prefix}/{name}"},
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": meta.get("category", "developer-tools"),
                }
            )
        else:
            entries.append(
                {
                    "name": name,
                    "source": f"{source_prefix}/{name}",
                    "description": meta["description"].strip(),
                    "category": meta.get("category"),
                    "tags": meta.get("tags", []),
                }
            )
    data: dict[str, Any] = {
        "name": manifest.get("marketplace", {}).get("name", "skills"),
        "metadata": {
            "description": manifest.get("marketplace", {})
            .get("description", "Portable skills")
            .strip(),
        },
        "plugins": entries,
    }
    if platform in {"claude", "codex"}:
        data["owner"] = author
    if platform == "codex":
        data["interface"] = {"displayName": "Dasobral Skills"}
    return data


def export_platform(
    root: Path | None = None,
    platform: str = "cursor",
    output_dir: Path | None = None,
    *,
    plugins: list[str] | None = None,
) -> list[Path]:
    """Write assembled plugins to output_dir (default: dist/<platform>/)."""
    root = root or repo_root()
    if platform not in PLATFORMS:
        raise ValueError(f"Unknown platform: {platform}")
    output_dir = output_dir or (root / "dist" / platform)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(root)
    names = platform_plugin_names(manifest, platform)
    if plugins is not None:
        names = [n for n in plugins if n in names]

    results = [assemble_plugin(root, platform, name, output_dir) for name in names]

    # Marketplace next to plugins for local use
    if platform == "cursor":
        prefix = "."
        market = _marketplace_entries(root, platform, names, source_prefix=prefix)
        # Cursor dist marketplace uses bare plugin names as source
        for entry in market["plugins"]:
            entry["source"] = Path(entry["source"]).name
        _write_json(output_dir / ".cursor-plugin" / "marketplace.json", market)
    elif platform == "claude":
        market = _marketplace_entries(
            root, platform, names, source_prefix="./plugins/claude"
        )
        # For dist layout, plugins live at dist/claude/<name>, so adjust:
        for entry in market["plugins"]:
            entry["source"] = f"./{Path(entry['source']).name}"
        _write_json(output_dir / ".claude-plugin" / "marketplace.json", market)
    else:
        market = _marketplace_entries(
            root, platform, names, source_prefix=f"./plugins/codex"
        )
        # When exporting to dist/codex, rewrite sources to ./<name>
        for entry in market["plugins"]:
            entry["source"]["path"] = f"./{entry['name']}"
        _write_json(output_dir / "marketplace.json", market)

    return results


def export_flat_skills(
    root: Path | None = None,
    output_dir: Path | None = None,
    *,
    platform: str = "claude",
    plugins: list[str] | None = None,
) -> Path:
    """Write a flat skills/ tree (compatibility install)."""
    root = root or repo_root()
    output_dir = output_dir or (root / "dist" / platform)
    flat = output_dir / "skills"
    if flat.exists():
        shutil.rmtree(flat)
    flat.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(root)
    names = platform_plugin_names(manifest, platform)
    if plugins is not None:
        names = [n for n in plugins if n in names]
    seen: set[str] = set()
    for name in names:
        for skill in plugin_skill_names(manifest, name):
            if skill in seen:
                continue
            seen.add(skill)
            copy_skill(root, skill, flat / skill)
    return flat


def export_all(root: Path | None = None, plugins: list[str] | None = None) -> dict[str, Path]:
    root = root or repo_root()
    out: dict[str, Path] = {}
    for platform in PLATFORMS:
        path = root / "dist" / platform
        export_platform(root, platform, path, plugins=plugins)
        out[platform] = path
    return out
