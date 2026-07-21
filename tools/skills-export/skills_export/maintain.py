from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exporters.claude import export_claude
from .exporters.codex import export_codex, export_codex_plugins
from .exporters.cursor import export_cursor
from .ingest import ingest_landing, landing_dir, write_ingest_report
from .manifest import (
    claude_plugins_dir,
    codex_plugins_dir,
    cursor_plugins_dir,
    load_manifest,
    platform_plugin_names,
    repo_root,
)
from .validate import validate_core
from .validate_claude import validate_claude_plugins
from .validate_codex import validate_codex_plugins
from .validate_cursor import validate_cursor_plugins


PLATFORMS = ("cursor", "claude", "codex")


@dataclass
class MaintainResult:
    ingest_skills: list[str] = field(default_factory=list)
    ingest_errors: list[str] = field(default_factory=list)
    validate_errors: list[str] = field(default_factory=list)
    exports: dict[str, str] = field(default_factory=dict)
    export_counts: dict[str, int] = field(default_factory=dict)
    dry_run: bool = False

    def ok(self) -> bool:
        return not self.ingest_errors and not self.validate_errors


def _sync_platform(
    root: Path,
    platform: str,
    *,
    plugins: list[str] | None,
) -> list[Path]:
    if platform == "cursor":
        return export_cursor(
            root, cursor_plugins_dir(root), plugins=plugins, sync_root=True
        )
    if platform == "claude":
        return export_claude(
            root, claude_plugins_dir(root), plugins=plugins, sync_root=True
        )
    return export_codex_plugins(root, codex_plugins_dir(root), plugins=plugins)


def _validate_platform(root: Path, platform: str) -> list[str]:
    if platform == "cursor":
        issues = validate_cursor_plugins(root)
    elif platform == "claude":
        issues = validate_claude_plugins(root)
    else:
        issues = validate_codex_plugins(root)
    return [f"{issue.path}: {issue.message}" for issue in issues]


def maintain(
    root: Path | None = None,
    *,
    dry_run: bool = False,
    skip_ingest: bool = False,
    skip_export: bool = False,
    plugins: list[str] | None = None,
) -> MaintainResult:
    """Full pipeline: landing → core → sync all platforms."""
    root = root or repo_root()
    result = MaintainResult(dry_run=dry_run)

    if not skip_ingest:
        ingest_result = ingest_landing(root, dry_run=dry_run)
        result.ingest_skills = ingest_result.ingested_skills
        result.ingest_errors = ingest_result.errors
        if not dry_run:
            write_ingest_report(root, ingest_result)
        if not ingest_result.ok():
            return result

    result.validate_errors = validate_core(root)
    if result.validate_errors:
        return result

    if not skip_export:
        manifest = load_manifest(root)
        result.exports = {
            "cursor": str(cursor_plugins_dir(root)),
            "claude": str(claude_plugins_dir(root)),
            "codex": str(codex_plugins_dir(root)),
        }
        for platform in PLATFORMS:
            names = platform_plugin_names(manifest, platform)
            if plugins is not None:
                names = [name for name in plugins if name in names]
            result.export_counts[platform] = len(names)

        if dry_run:
            return result

        for platform in PLATFORMS:
            _sync_platform(root, platform, plugins=plugins)

        for platform in PLATFORMS:
            result.validate_errors.extend(_validate_platform(root, platform))
            if result.validate_errors:
                return result

        # Optional flat compatibility exports (not the primary path).
        export_claude(root, root / "dist" / "claude", plugins=plugins, flat=True)
        export_codex(root, flat_output_dir=root / "dist" / "codex", plugins=plugins)

    if dry_run:
        return result

    report_path = landing_dir(root) / "last-maintain.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "ok": result.ok(),
        "ingested_skills": result.ingest_skills,
        "exports": result.exports,
        "errors": result.ingest_errors + result.validate_errors,
    }
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return result
