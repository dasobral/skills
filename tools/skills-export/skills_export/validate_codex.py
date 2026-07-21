"""Minimal Codex plugin tree checks (no committed plugins required)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .manifest import load_manifest, platform_plugin_names


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str


def validate_codex_plugins(root: Path) -> list[ValidationIssue]:
    """Validate plugins/codex or dist/codex if present."""
    manifest = load_manifest(root)
    expected = platform_plugin_names(manifest, "codex")
    issues: list[ValidationIssue] = []
    for candidate in (root / "plugins" / "codex", root / "dist" / "codex"):
        if not candidate.is_dir():
            continue
        for name in expected:
            plugin = candidate / name
            if not plugin.is_dir():
                # allow filtered export trees
                continue
            plugin_json = plugin / ".codex-plugin" / "plugin.json"
            if not plugin_json.is_file():
                issues.append(ValidationIssue(plugin_json, "missing plugin.json"))
            skills = plugin / "skills"
            if not skills.is_dir():
                issues.append(ValidationIssue(skills, "missing skills/"))
                continue
            for skill in manifest["plugins"][name]["skills"]:
                if not (skills / skill / "SKILL.md").is_file():
                    issues.append(
                        ValidationIssue(skills / skill, f"missing skill {skill}")
                    )
        return issues
    issues.append(ValidationIssue(root / "dist" / "codex", "no Codex plugins exported"))
    return issues
