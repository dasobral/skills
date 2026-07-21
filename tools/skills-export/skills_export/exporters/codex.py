"""Codex export shims — prefer skills_export.assemble."""
from __future__ import annotations

import json
from pathlib import Path

from ..assemble import assemble_plugin, export_flat_skills, export_platform
from ..manifest import load_manifest, repo_root


def export_codex_plugin(root, plugin_name, output_root, *, clean=True):
    return assemble_plugin(Path(root), "codex", plugin_name, Path(output_root))


def export_codex_plugins(root=None, output_root=None, *, plugins=None, clean=True):
    root = Path(root) if root else repo_root()
    output_root = Path(output_root) if output_root else root / "dist" / "codex"
    return export_platform(root, "codex", output_root, plugins=plugins)


def export_codex_marketplace(root=None, output_path=None):
    """Write Codex marketplace next to exported plugins (dist/codex/marketplace.json)."""
    root = Path(root) if root else repo_root()
    # Ensure plugins exist under dist/codex
    out = root / "dist" / "codex"
    if not out.is_dir():
        export_platform(root, "codex", out)
    market = out / "marketplace.json"
    if output_path is not None:
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(market.read_text(encoding="utf-8"), encoding="utf-8")
        return dest
    # Also write repo-style path for tests that expect .agents/plugins/
    agents_market = root / ".agents" / "plugins" / "marketplace.json"
    agents_market.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(market.read_text(encoding="utf-8"))
    for entry in data.get("plugins", []):
        if isinstance(entry.get("source"), dict):
            entry["source"]["path"] = f"./plugins/codex/{entry['name']}"
    # Copy plugins to plugins/codex for marketplace-relative layout in tests
    plugins_dest = root / "plugins" / "codex"
    if plugins_dest.exists():
        import shutil

        shutil.rmtree(plugins_dest)
    import shutil

    shutil.copytree(out, plugins_dest, ignore=shutil.ignore_patterns("marketplace.json"))
    agents_market.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return agents_market


def export_codex(root=None, output_dir=None, *, flat_output_dir=None, plugins=None, flat=True, native=False, bundles=None):
    if bundles is not None:
        raise ValueError("legacy Codex bundles were removed")
    root = Path(root) if root else repo_root()
    dest = flat_output_dir or output_dir or root / "dist" / "codex"
    results = []
    if flat:
        results.append(export_flat_skills(root, dest, platform="codex", plugins=plugins))
    if native:
        results.extend(export_platform(root, "codex", dest, plugins=plugins))
    if not results:
        raise ValueError("Codex export requested no artifacts")
    return results
