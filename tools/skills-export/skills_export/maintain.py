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
    codex_plugins_dir,
    cursor_plugins_dir,
    load_manifest,
    platform_plugin_names,
    repo_root,
)
from .validate import validate_core
from .validate_codex import validate_codex_plugins
from .validate_cursor import validate_cursor_plugins


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


def maintain(
    root: Path | None = None,
    *,
    dry_run: bool = False,
    skip_ingest: bool = False,
    skip_export: bool = False,
    plugins: list[str] | None = None,
) -> MaintainResult:
    """Full autonomous pipeline: landing → core → all platforms."""
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
        cursor_out = cursor_plugins_dir(root)
        codex_native_out = codex_plugins_dir(root)
        claude_out = root / "dist" / "claude"
        codex_flat_out = root / "dist" / "codex"
        result.exports = {
            "cursor": str(cursor_out),
            "codex": str(codex_native_out),
            "claude": str(claude_out),
            "codex-flat": str(codex_flat_out),
        }
        manifest = load_manifest(root)
        cursor_names = platform_plugin_names(manifest, "cursor")
        codex_names = list(manifest["plugins"])
        if plugins is not None:
            cursor_names = [name for name in plugins if name in cursor_names]
            codex_names = [name for name in plugins if name in codex_names]
        result.export_counts = {
            "cursor": len(cursor_names),
            "codex": len(codex_names),
        }

        if dry_run:
            return result

        export_cursor(root, cursor_out, plugins=plugins, sync_root=True)
        export_codex_plugins(root, codex_native_out, plugins=plugins)

        cursor_issues = validate_cursor_plugins(root)
        codex_issues = validate_codex_plugins(root)
        if cursor_issues or codex_issues:
            result.validate_errors.extend(
                f"{issue.path}: {issue.message}"
                for issue in [*cursor_issues, *codex_issues]
            )
            return result

        export_claude(root, claude_out, plugins=plugins)
        export_codex(
            root,
            flat_output_dir=codex_flat_out,
            plugins=plugins,
        )

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
