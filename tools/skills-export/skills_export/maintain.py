from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exporters.claude import export_claude
from .exporters.codex import export_codex
from .exporters.cursor import export_cursor
from .ingest import ingest_landing, landing_dir, write_ingest_report
from .manifest import repo_root
from .validate import validate_core


@dataclass
class MaintainResult:
    ingest_skills: list[str] = field(default_factory=list)
    ingest_errors: list[str] = field(default_factory=list)
    validate_errors: list[str] = field(default_factory=list)
    exports: dict[str, str] = field(default_factory=dict)
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
        write_ingest_report(root, ingest_result)
        if not ingest_result.ok():
            return result

    if dry_run:
        return result

    result.validate_errors = validate_core(root)
    if result.validate_errors:
        return result

    if not skip_export:
        from .manifest import cursor_plugins_dir

        cursor_out = cursor_plugins_dir(root)
        export_cursor(root, cursor_out, plugins=plugins, sync_root=True)
        result.exports["cursor"] = str(cursor_out)

        claude_out = root / "dist" / "claude"
        export_claude(root, claude_out, plugins=plugins)
        result.exports["claude"] = str(claude_out)

        codex_out = root / "dist" / "codex"
        export_codex(root, codex_out, plugins=plugins)
        result.exports["codex"] = str(codex_out)

    report_path = landing_dir(root) / "last-maintain.json"
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
