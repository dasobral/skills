from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import load_manifest, platform_plugin_names


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str


def _reported(root: Path, path: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _add(
    issues: list[ValidationIssue],
    root: Path,
    path: Path,
    message: str,
) -> None:
    issues.append(ValidationIssue(_reported(root, path), message))


def _safe_component(
    root: Path,
    plugin_root: Path,
    owner: Path,
    field: str,
    raw: object,
    issues: list[ValidationIssue],
) -> Path | None:
    label = f"component path '{field}'"
    if not isinstance(raw, str):
        _add(issues, root, owner, f"{label} must be a string")
        return None
    path = Path(raw)
    if not raw.startswith("./"):
        _add(issues, root, owner, f"{label} must begin with './'")
        return None
    if path.is_absolute() or ".." in path.parts:
        _add(issues, root, owner, f"{label} must be a relative path without '..'")
        return None
    resolved = (plugin_root / path).resolve()
    if not resolved.is_relative_to(plugin_root.resolve()):
        _add(issues, root, owner, f"{label} escapes plugin root")
        return None
    if not resolved.exists():
        _add(issues, root, owner, f"{label} referenced path does not exist")
        return None
    return resolved


def _validate_skills(
    root: Path,
    skills_dir: Path,
    expected: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    if not skills_dir.is_dir():
        _add(issues, root, skills_dir, "skills component must be a directory")
        return
    generated = {path.name for path in skills_dir.iterdir() if path.is_dir()}
    expected_skills = set(expected.get("skills", []))
    for skill_name in expected_skills:
        if skill_name not in generated:
            _add(
                issues,
                root,
                skills_dir,
                f"missing generated core skill '{skill_name}'",
            )
    for skill_name in sorted(generated - expected_skills):
        _add(
            issues,
            root,
            skills_dir / skill_name,
            f"unexpected generated skill '{skill_name}'",
        )
    for skill_dir in sorted(
        (path for path in skills_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    ):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            _add(issues, root, skill_dir, "skill is missing SKILL.md")


def _validate_plugin(
    root: Path,
    plugin_name: str,
    plugin_meta: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    plugin_root = root / "plugins" / "claude" / plugin_name
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        _add(issues, root, plugin_root, "missing .claude-plugin/plugin.json")
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(issues, root, manifest_path, f"invalid plugin.json: {exc}")
        return
    if not isinstance(data, dict):
        _add(issues, root, manifest_path, "plugin.json must be an object")
        return
    if data.get("name") != plugin_name:
        _add(issues, root, manifest_path, "plugin name must match directory")
    if "skills" not in data:
        _add(issues, root, manifest_path, "plugin manifest is missing skills")
        return
    skills_path = _safe_component(
        root, plugin_root, manifest_path, "skills", data["skills"], issues
    )
    if skills_path is not None:
        _validate_skills(root, skills_path, plugin_meta, issues)
    for field in ("agents", "hooks", "commands", "mcpServers"):
        if field in data:
            _safe_component(
                root, plugin_root, manifest_path, field, data[field], issues
            )


def _validate_marketplace(
    root: Path,
    expected_names: list[str],
    issues: list[ValidationIssue],
) -> None:
    path = root / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        _add(issues, root, path, "missing Claude marketplace.json")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(issues, root, path, f"invalid marketplace.json: {exc}")
        return
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        _add(issues, root, path, "marketplace plugins must be a list")
        return
    names: list[str] = []
    for entry in plugins:
        if not isinstance(entry, dict):
            _add(issues, root, path, "marketplace plugin entry must be an object")
            continue
        name = entry.get("name")
        source = entry.get("source")
        if not isinstance(name, str) or not NAME_RE.match(name):
            _add(issues, root, path, f"invalid marketplace plugin name: {name!r}")
            continue
        expected_source = f"./plugins/claude/{name}"
        if source != expected_source:
            _add(
                issues,
                root,
                path,
                f"marketplace source for '{name}' must be '{expected_source}'",
            )
        names.append(name)
    if sorted(names) != sorted(expected_names):
        _add(
            issues,
            root,
            path,
            "marketplace plugin list does not match Claude plugins in manifest",
        )


def validate_claude_plugins(root: Path) -> list[ValidationIssue]:
    manifest = load_manifest(root)
    issues: list[ValidationIssue] = []
    expected = platform_plugin_names(manifest, "claude")
    plugins_root = root / "plugins" / "claude"

    if not plugins_root.is_dir():
        _add(issues, root, plugins_root, "missing plugins/claude/")
        return issues

    generated = {
        path.name
        for path in plugins_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    for name in expected:
        if name not in generated:
            _add(issues, root, plugins_root / name, "missing generated Claude plugin")
        else:
            _validate_plugin(root, name, manifest["plugins"][name], issues)
    for name in sorted(generated - set(expected)):
        _add(
            issues,
            root,
            plugins_root / name,
            f"unexpected Claude plugin '{name}' not declared in manifest",
        )

    _validate_marketplace(root, expected, issues)
    return issues
