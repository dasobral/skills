from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def repo_root(start: Path | None = None) -> Path:
    path = (start or Path.cwd()).resolve()
    for candidate in [path, *path.parents]:
        if (candidate / "core" / "manifest.yaml").is_file():
            return candidate
    raise FileNotFoundError("Could not find core/manifest.yaml (run from repo root)")


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    manifest_path = root / "core" / "manifest.yaml"
    with manifest_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "plugins" not in data:
        raise ValueError(f"Invalid manifest: {manifest_path}")
    return data


def core_skills_dir(root: Path) -> Path:
    return root / "core" / "skills"


def cursor_adapter_dir(root: Path, plugin: str) -> Path:
    return root / "adapters" / "cursor" / plugin


def cursor_plugins_dir(root: Path) -> Path:
    """Generated Cursor plugins live under plugins/cursor/ (not repo root)."""
    return root / "plugins" / "cursor"


def codex_adapter_dir(root: Path, plugin_name: str) -> Path:
    return root / "adapters" / "codex" / plugin_name


def codex_plugins_dir(root: Path) -> Path:
    return root / "plugins" / "codex"


def plugin_skill_names(manifest: dict[str, Any], plugin: str) -> list[str]:
    plugins = manifest["plugins"]
    if plugin not in plugins:
        raise KeyError(f"Unknown plugin: {plugin}")
    return list(plugins[plugin]["skills"])


def platform_plugin_names(
    manifest: dict[str, Any],
    platform: str,
) -> list[str]:
    return [
        name
        for name, metadata in manifest["plugins"].items()
        if platform in metadata
    ]


def all_skill_names(manifest: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for plugin in manifest["plugins"].values():
        for skill in plugin["skills"]:
            if skill not in names:
                names.append(skill)
    return names


def read_skill_frontmatter(skill_dir: Path) -> dict[str, str]:
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def copy_tree(src: Path, dst: Path) -> None:
    import shutil

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def enrich_skill(skill_dst: Path, root: Path) -> None:
    """Inject shared platform reference docs into an exported skill."""
    import shutil

    refs = skill_dst / "references"
    refs.mkdir(parents=True, exist_ok=True)
    for name in ("platform-paths.md", "platform-orchestration.md"):
        src = root / "core" / "references" / name
        if src.is_file():
            shutil.copy2(src, refs / name)


def copy_skill(root: Path, skill_name: str, dst: Path) -> None:
    copy_tree(core_skills_dir(root) / skill_name, dst)
    enrich_skill(dst, root)


def copy_file(src: Path, dst: Path) -> None:
    import shutil
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
