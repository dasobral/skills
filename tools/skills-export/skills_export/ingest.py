from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .manifest import core_skills_dir, load_manifest, repo_root
from .normalize import normalize_skill_dir, validate_skill_dir


def landing_dir(root: Path) -> Path:
    return root / "landing"


def landing_skills_dir(root: Path) -> Path:
    return landing_dir(root) / "skills"


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
    errors: list[str] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)
    dry_run: bool = False

    def ok(self) -> bool:
        return not self.errors


def _find_skill_dirs(base: Path) -> list[Path]:
    """Find direct child skill directories under base."""
    if not base.is_dir():
        return []
    return [
        child
        for child in sorted(base.iterdir())
        if child.is_dir()
        and not child.name.startswith(".")
        and (child / "SKILL.md").is_file()
    ]


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
            # New plugins get all platforms by default; adapters own scaffolding.
            entry.setdefault("claude", {})
            entry.setdefault("codex", {"agents": False, "hooks": False})
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
    dry_run: bool,
) -> None:
    dst = core_skills_dir(root) / skill_name
    if dry_run:
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("landing.yaml"))
    normalize_skill_dir(dst, skill_name, source_platform="portable")


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
    """Ingest portable skills from landing/skills/ into core/.

    Unique ingest path: only landing/skills/<skill>/. Platform scaffolding is
    never ingested; author it under adapters/<platform>/<plugin>/.
    """
    root = root or repo_root()
    result = IngestResult(dry_run=dry_run)
    manifest = load_manifest(root)
    registry = load_landing_registry(root)
    archive_base = _archive_path(root)

    for skill_dir in _find_skill_dirs(landing_skills_dir(root)):
        skill_name = skill_dir.name
        errs = validate_skill_dir(skill_dir, skill_name)
        if errs:
            result.errors.extend(errs)
            continue
        landing_meta = read_landing_meta(skill_dir)
        try:
            _assign_skill_to_plugin(manifest, registry, skill_name, landing_meta)
            _ingest_skill_to_core(root, skill_dir, skill_name, dry_run=dry_run)
            result.ingested_skills.append(skill_name)
            rel = _archive_item(root, skill_dir, archive_base / "skills", dry_run=dry_run)
            if rel:
                result.archived.append(rel)
        except (KeyError, ValueError) as exc:
            result.errors.append(str(exc))

    if not dry_run and result.ok() and result.ingested_skills:
        save_manifest(root, manifest)

    return result


def write_ingest_report(root: Path, result: IngestResult, path: Path | None = None) -> Path:
    out = path or (landing_dir(root) / "last-maintain.json")
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": result.dry_run,
        "ok": result.ok(),
        "ingested_skills": result.ingested_skills,
        "archived": result.archived,
        "errors": result.errors,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out
