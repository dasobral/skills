from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .manifest import (
    copy_tree,
    core_skills_dir,
    cursor_adapter_dir,
    load_manifest,
    repo_root,
)
from .normalize import normalize_skill_dir, validate_skill_dir


def landing_dir(root: Path) -> Path:
    return root / "landing"


def load_landing_registry(root: Path) -> dict[str, Any]:
    path = landing_dir(root) / "registry.yaml"
    if not path.is_file():
        return {"default_plugin": "codecraft", "assignments": {}, "new_plugins": {}}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("default_plugin", "codecraft")
    data.setdefault("assignments", {})
    data.setdefault("new_plugins", {})
    return data


def save_manifest(root: Path, manifest: dict[str, Any]) -> None:
    path = root / "core" / "manifest.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)


def read_landing_meta(skill_dir: Path) -> dict[str, Any]:
    meta_path = skill_dir / "landing.yaml"
    if not meta_path.is_file():
        return {}
    with meta_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class IngestResult:
    ingested_skills: list[str] = field(default_factory=list)
    ingested_plugins: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)
    dry_run: bool = False

    def ok(self) -> bool:
        return not self.errors


def _find_skill_dirs(base: Path) -> list[Path]:
    """Find skill directories under base (supports nested .claude/skills layouts)."""
    found: list[Path] = []
    if not base.is_dir():
        return found

    # Direct child with SKILL.md
    for child in sorted(base.iterdir()):
        if child.is_dir() and (child / "SKILL.md").is_file():
            found.append(child)

    # Nested platform layouts
    for nested in (
        base / "skills",
        base / ".claude" / "skills",
        base / ".agents" / "skills",
    ):
        if nested.is_dir():
            for child in sorted(nested.iterdir()):
                if child.is_dir() and (child / "SKILL.md").is_file():
                    found.append(child)

    return found


def _assign_skill_to_plugin(
    manifest: dict[str, Any],
    registry: dict[str, Any],
    skill_name: str,
    landing_meta: dict[str, Any],
) -> str:
    plugin = landing_meta.get("plugin") or registry["assignments"].get(skill_name)
    if not plugin:
        plugin = registry["default_plugin"]

    new_plugins = registry.get("new_plugins") or {}
    if plugin not in manifest["plugins"]:
        if plugin in new_plugins:
            entry = dict(new_plugins[plugin])
            entry.setdefault("skills", [])
            entry.setdefault("version", "1.0.0")
            entry.setdefault("category", "developer-tools")
            entry.setdefault("keywords", [])
            entry.setdefault("tags", [])
            manifest["plugins"][plugin] = entry
        else:
            raise KeyError(
                f"Plugin '{plugin}' not in core/manifest.yaml — "
                f"add to landing/registry.yaml new_plugins or core/manifest.yaml"
            )

    skills = manifest["plugins"][plugin].setdefault("skills", [])
    if skill_name not in skills:
        skills.append(skill_name)
    return plugin


def _ingest_skill_to_core(
    root: Path,
    src: Path,
    skill_name: str,
    *,
    source_platform: str,
    dry_run: bool,
) -> None:
    dst = core_skills_dir(root) / skill_name
    if dry_run:
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("landing.yaml"))
    normalize_skill_dir(dst, skill_name, source_platform=source_platform)


def _ingest_cursor_plugin(
    root: Path,
    plugin_src: Path,
    registry: dict[str, Any],
    manifest: dict[str, Any],
    result: IngestResult,
    *,
    dry_run: bool,
) -> None:
    plugin_name = plugin_src.name
    skills_src = plugin_src / "skills"
    if not skills_src.is_dir():
        result.errors.append(f"cursor plugin '{plugin_name}': missing skills/")
        return

    adapter_dst = cursor_adapter_dir(root, plugin_name)
    if not dry_run:
        adapter_dst.mkdir(parents=True, exist_ok=True)

    for skill_dir in _find_skill_dirs(skills_src):
        skill_name = skill_dir.name
        errs = validate_skill_dir(skill_dir, skill_name)
        if errs:
            result.errors.extend(errs)
            continue
        landing_meta = read_landing_meta(skill_dir)
        try:
            plugin = landing_meta.get("plugin") or plugin_name
            _assign_skill_to_plugin(manifest, registry, skill_name, {"plugin": plugin})
            _ingest_skill_to_core(
                root, skill_dir, skill_name, source_platform="cursor", dry_run=dry_run
            )
            result.ingested_skills.append(skill_name)
        except (KeyError, ValueError) as exc:
            result.errors.append(str(exc))

    if not dry_run:
        for component in ("agents", "hooks", "rules"):
            src = plugin_src / component
            if src.exists():
                copy_tree(src, adapter_dst / component)
        plugin_json = plugin_src / ".cursor-plugin" / "plugin.json"
        if plugin_json.is_file():
            shutil.copy2(plugin_json, adapter_dst / "plugin.json")
        readme = plugin_src / "README.md"
        if readme.is_file():
            shutil.copy2(readme, adapter_dst / "README.md")

    if plugin_name not in result.ingested_plugins:
        result.ingested_plugins.append(plugin_name)


def _archive_path(root: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return landing_dir(root) / "processed" / ts


def _archive_item(
    root: Path, src: Path, archive_base: Path, *, dry_run: bool
) -> str | None:
    if dry_run:
        return None
    archive_base.mkdir(parents=True, exist_ok=True)
    dst = archive_base / src.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(src), str(dst))
    return str(dst.relative_to(root))


def ingest_landing(root: Path | None = None, *, dry_run: bool = False) -> IngestResult:
    root = root or repo_root()
    result = IngestResult(dry_run=dry_run)
    manifest = load_manifest(root)
    registry = load_landing_registry(root)
    archive_base = _archive_path(root)

    # 1. Portable skills: landing/skills/
    portable_base = landing_dir(root) / "skills"
    for skill_dir in _find_skill_dirs(portable_base):
        if skill_dir.name.startswith("."):
            continue
        skill_name = skill_dir.name
        errs = validate_skill_dir(skill_dir, skill_name)
        if errs:
            result.errors.extend(errs)
            continue
        landing_meta = read_landing_meta(skill_dir)
        try:
            plugin = _assign_skill_to_plugin(manifest, registry, skill_name, landing_meta)
            _ingest_skill_to_core(
                root, skill_dir, skill_name, source_platform="portable", dry_run=dry_run
            )
            result.ingested_skills.append(skill_name)
            rel = _archive_item(root, skill_dir, archive_base / "skills", dry_run=dry_run)
            if rel:
                result.archived.append(rel)
        except (KeyError, ValueError) as exc:
            result.errors.append(str(exc))

    # 2. Platform incoming: claude, codex (flat skill folders)
    for platform in ("claude", "codex"):
        incoming = landing_dir(root) / "incoming" / platform
        for skill_dir in _find_skill_dirs(incoming):
            skill_name = skill_dir.name
            errs = validate_skill_dir(skill_dir, skill_name)
            if errs:
                result.errors.extend(errs)
                continue
            landing_meta = read_landing_meta(skill_dir)
            try:
                _assign_skill_to_plugin(manifest, registry, skill_name, landing_meta)
                _ingest_skill_to_core(
                    root, skill_dir, skill_name, source_platform=platform, dry_run=dry_run
                )
                result.ingested_skills.append(skill_name)
                rel = _archive_item(
                    root, skill_dir, archive_base / "incoming" / platform, dry_run=dry_run
                )
                if rel:
                    result.archived.append(rel)
            except (KeyError, ValueError) as exc:
                result.errors.append(str(exc))

    # 3. Cursor plugins: landing/incoming/cursor/<plugin>/
    cursor_incoming = landing_dir(root) / "incoming" / "cursor"
    if cursor_incoming.is_dir():
        for plugin_dir in sorted(cursor_incoming.iterdir()):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue
            if (plugin_dir / "skills").is_dir() or (plugin_dir / ".cursor-plugin").is_dir():
                before_errors = len(result.errors)
                _ingest_cursor_plugin(
                    root, plugin_dir, registry, manifest, result, dry_run=dry_run
                )
                if len(result.errors) == before_errors:
                    rel = _archive_item(
                        root,
                        plugin_dir,
                        archive_base / "incoming" / "cursor",
                        dry_run=dry_run,
                    )
                    if rel:
                        result.archived.append(rel)

    if not dry_run and result.ok():
        save_manifest(root, manifest)

    return result


def write_ingest_report(root: Path, result: IngestResult, path: Path | None = None) -> Path:
    out = path or (landing_dir(root) / "last-maintain.json")
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": result.dry_run,
        "ok": result.ok(),
        "ingested_skills": result.ingested_skills,
        "ingested_plugins": result.ingested_plugins,
        "archived": result.archived,
        "errors": result.errors,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out
