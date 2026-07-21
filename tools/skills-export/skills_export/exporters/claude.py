from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..manifest import (
    claude_adapter_dir,
    claude_plugins_dir,
    copy_skill,
    copy_tree,
    load_manifest,
    platform_plugin_names,
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
        "version": plugin_meta["version"],
        "description": plugin_meta["description"].strip(),
        "author": manifest.get("author", {"name": "Unknown"}),
        "license": manifest.get("license", "MIT"),
        "keywords": plugin_meta.get("keywords", []),
        "skills": "./skills/",
    }
    if plugin_meta.get("display_name"):
        base["displayName"] = plugin_meta["display_name"]

    adapter_json = adapter / "plugin.json"
    if adapter_json.is_file():
        overlay = json.loads(adapter_json.read_text(encoding="utf-8"))
        claude_cfg = plugin_meta.get("claude", {})
        for key in ("agents", "hooks", "commands", "mcpServers"):
            if claude_cfg.get(key) and key in overlay:
                base[key] = overlay[key]
            elif key in overlay and overlay[key]:
                base[key] = overlay[key]
        for key in ("homepage", "repository", "category", "tags"):
            if key in overlay:
                base[key] = overlay[key]
    return base


def _default_readme(plugin_name: str, display_name: str, skills: list[str]) -> str:
    skill_list = "\n".join(f"- `{s}`" for s in skills)
    return f"""# {display_name}

Claude Code plugin generated from portable core.

## Skills

{skill_list}

## Install

From the skills repo marketplace:

```text
/plugin marketplace add .
/plugin install {plugin_name}@dasobral-skills
```

Or copy this directory into a Claude Code plugins path.
"""


def export_claude_plugin(
    root: Path,
    plugin_name: str,
    output_dir: Path,
    *,
    clean: bool = True,
) -> Path:
    """Assemble one Claude plugin: core skills + adapter scaffolding."""
    manifest = load_manifest(root)
    if plugin_name not in platform_plugin_names(manifest, "claude"):
        raise ValueError(f"Plugin does not declare Claude support: {plugin_name}")

    plugin_out = output_dir / plugin_name
    if clean and plugin_out.exists():
        shutil.rmtree(plugin_out)

    adapter = claude_adapter_dir(root, plugin_name)
    skills_out = plugin_out / "skills"
    skills_out.mkdir(parents=True, exist_ok=True)

    skill_names = plugin_skill_names(manifest, plugin_name)
    for skill in skill_names:
        copy_skill(root, skill, skills_out / skill)

    plugin_json = _assemble_plugin_json(manifest, plugin_name, adapter)
    _write_json(plugin_out / ".claude-plugin" / "plugin.json", plugin_json)

    for component in ("agents", "hooks", "commands"):
        src = adapter / component
        if src.exists():
            copy_tree(src, plugin_out / component)

    mcp = adapter / ".mcp.json"
    if mcp.is_file():
        shutil.copy2(mcp, plugin_out / ".mcp.json")

    readme = adapter / "README.md"
    if readme.is_file():
        shutil.copy2(readme, plugin_out / "README.md")
    else:
        (plugin_out / "README.md").write_text(
            _default_readme(
                plugin_name,
                manifest["plugins"][plugin_name]["display_name"],
                skill_names,
            ),
            encoding="utf-8",
        )

    return plugin_out


def export_claude_marketplace(
    root: Path,
    output_dir: Path,
    *,
    sync_plugins: bool = False,
    plugins: list[str] | None = None,
) -> Path:
    """Write Claude marketplace.json at .claude-plugin/marketplace.json when syncing."""
    manifest = load_manifest(root)
    marketplace_path = root / ".claude-plugin" / "marketplace.json"
    supported = platform_plugin_names(manifest, "claude")
    names = supported if sync_plugins or plugins is None else plugins

    author = manifest.get("author", {"name": "Unknown"})
    entries = []
    for name in names:
        meta = manifest["plugins"][name]
        source = (
            f"./plugins/claude/{name}" if sync_plugins else f"./{name}"
        )
        entries.append(
            {
                "name": name,
                "source": source,
                "description": meta["description"].strip(),
                "version": meta["version"],
                "category": meta.get("category"),
                "tags": meta.get("tags", []),
            }
        )

    data = {
        "name": manifest.get("marketplace", {}).get("name", "skills"),
        "owner": author,
        "metadata": {
            "description": manifest.get("marketplace", {})
            .get("description", "Portable skills marketplace")
            .strip(),
        },
        "plugins": entries,
    }

    if sync_plugins and marketplace_path.is_file():
        prev = json.loads(marketplace_path.read_text(encoding="utf-8"))
        if isinstance(prev.get("owner"), dict):
            data["owner"] = prev["owner"]
        if isinstance(prev.get("metadata"), dict) and prev["metadata"].get("description"):
            data["metadata"]["description"] = prev["metadata"]["description"]

    if sync_plugins:
        dest = marketplace_path
    else:
        dest = output_dir / ".claude-plugin" / "marketplace.json"
    _write_json(dest, data)
    return dest


def export_claude_flat(root: Path, output_dir: Path, *, clean: bool = True) -> Path:
    """Optional flat skills under output_dir/skills for non-plugin install."""
    manifest = load_manifest(root)
    flat = output_dir / "skills"
    if clean and flat.exists():
        shutil.rmtree(flat)
    flat.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    for name in platform_plugin_names(manifest, "claude"):
        for skill in plugin_skill_names(manifest, name):
            if skill in seen:
                continue
            seen.add(skill)
            copy_skill(root, skill, flat / skill)

    (output_dir / "README.md").write_text(
        """# Claude Code skills (flat export)

Compatibility export. Prefer native plugins under `plugins/claude/`.

```bash
cp -r skills/* ~/.claude/skills/
```
""",
        encoding="utf-8",
    )
    return flat


def export_claude(
    root: Path | None = None,
    output_dir: Path | None = None,
    *,
    plugins: list[str] | None = None,
    sync_root: bool = False,
    flat: bool = False,
) -> list[Path]:
    """Export Claude plugins.

    sync_root=True writes to plugins/claude/ and refreshes .claude-plugin/marketplace.json.
    Otherwise writes to output_dir or dist/claude/.
    """
    root = root or repo_root()
    sync_plugins = sync_root
    if output_dir is None:
        output_dir = (
            claude_plugins_dir(root) if sync_plugins else root / "dist" / "claude"
        )
    elif sync_plugins and output_dir.resolve() == root.resolve():
        output_dir = claude_plugins_dir(root)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(root)
    supported = platform_plugin_names(manifest, "claude")
    if plugins is not None:
        unknown = [name for name in plugins if name not in manifest["plugins"]]
        if unknown:
            raise KeyError(f"Unknown plugin: {unknown[0]}")
        names = [name for name in plugins if name in supported]
    else:
        names = supported
        if sync_plugins and output_dir.is_dir():
            for path in list(output_dir.iterdir()):
                if path.name in names or not (path.is_dir() or path.is_symlink()):
                    continue
                if path.is_symlink():
                    path.unlink()
                else:
                    shutil.rmtree(path)

    results: list[Path] = []
    for name in names:
        results.append(export_claude_plugin(root, name, output_dir))

    export_claude_marketplace(
        root,
        output_dir,
        sync_plugins=sync_plugins,
        plugins=names,
    )

    if flat and not sync_plugins:
        results.append(export_claude_flat(root, output_dir))

    return results
