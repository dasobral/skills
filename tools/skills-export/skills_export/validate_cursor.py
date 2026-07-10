from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .manifest import load_manifest, platform_plugin_names


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMPONENT_FIELDS = ("skills", "agents", "rules", "hooks")


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
    if path.is_absolute():
        _add(issues, root, owner, f"{label} must be relative")
        return None
    if ".." in path.parts:
        _add(issues, root, owner, f"{label} must not contain '..'")
        return None
    current = plugin_root
    for part in path.parts:
        if part in ("", "."):
            continue
        current /= part
        if current.is_symlink():
            _add(issues, root, owner, f"{label} must not traverse a symlink")
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
    generated = {
        path.name for path in skills_dir.iterdir() if path.is_dir()
    }
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
            continue
        text = skill_md.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.DOTALL)
        if not match:
            _add(issues, root, skill_md, "skill is missing YAML frontmatter")
            continue
        try:
            metadata = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            _add(issues, root, skill_md, f"invalid skill frontmatter: {exc}")
            continue
        if not isinstance(metadata, dict):
            _add(issues, root, skill_md, "skill frontmatter must be an object")
            continue
        if metadata.get("name") != skill_dir.name:
            _add(
                issues,
                root,
                skill_md,
                "skill frontmatter name must match its directory",
            )
        if not str(metadata.get("description", "")).strip():
            _add(issues, root, skill_md, "skill is missing a description")


def _validate_plugin(
    root: Path,
    plugin_root: Path,
    expected: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    for path in plugin_root.rglob("*"):
        if path.is_symlink():
            _add(issues, root, path, "plugin tree must not contain symlinks")
    manifest_path = plugin_root / ".cursor-plugin" / "plugin.json"
    if not manifest_path.is_file():
        _add(issues, root, plugin_root, "missing .cursor-plugin/plugin.json")
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(issues, root, manifest_path, f"invalid JSON: {exc}")
        return
    if not isinstance(manifest, dict):
        _add(issues, root, manifest_path, "plugin manifest must be an object")
        return
    if manifest.get("name") != plugin_root.name:
        _add(issues, root, manifest_path, "plugin name must match its directory")
    if not NAME_RE.fullmatch(str(manifest.get("name", ""))):
        _add(issues, root, manifest_path, "plugin name must be lowercase kebab-case")
    expected_fields = {
        "displayName": expected.get("display_name"),
        "version": expected.get("version"),
        "description": str(expected.get("description", "")).strip(),
        "keywords": expected.get("keywords", []),
        "category": expected.get("category", "developer-tools"),
        "tags": expected.get("tags", []),
    }
    for field, value in expected_fields.items():
        actual = manifest.get(field)
        if field == "description":
            actual = str(actual or "").strip()
        if actual != value:
            _add(
                issues,
                root,
                manifest_path,
                f"plugin {field} does not match core manifest",
            )
    resolved: dict[str, Path] = {}
    for field in COMPONENT_FIELDS:
        if field in manifest:
            component = _safe_component(
                root,
                plugin_root,
                manifest_path,
                field,
                manifest[field],
                issues,
            )
            if component is not None:
                resolved[field] = component
    if "skills" not in manifest:
        _add(issues, root, manifest_path, "plugin manifest is missing skills")
    elif "skills" in resolved:
        _validate_skills(root, resolved["skills"], expected, issues)
    cursor_metadata = expected.get("cursor", {})
    for field in ("agents", "rules", "hooks"):
        required = bool(cursor_metadata.get(field))
        if required != (field in manifest):
            _add(
                issues,
                root,
                manifest_path,
                f"plugin {field} declaration does not match core manifest",
            )
        if field in resolved:
            if field == "hooks" and not resolved[field].is_file():
                _add(issues, root, resolved[field], "hooks component must be a file")
            elif field != "hooks" and not resolved[field].is_dir():
                _add(
                    issues,
                    root,
                    resolved[field],
                    f"{field} component must be a directory",
                )


def _validate_marketplace(
    root: Path,
    plugins: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    path = root / ".cursor-plugin" / "marketplace.json"
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            _add(issues, root, current, "marketplace must not traverse a symlink")
            return
    if not path.is_file():
        _add(issues, root, path, "missing generated Cursor marketplace")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(issues, root, path, f"invalid marketplace JSON: {exc}")
        return
    entries = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        _add(issues, root, path, "marketplace must contain a plugins list")
        return
    names: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            _add(issues, root, path, "marketplace plugin must be an object")
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            _add(issues, root, path, "marketplace plugin name must be a string")
            continue
        names.append(name)
        if name in seen:
            _add(issues, root, path, f"duplicate marketplace plugin: {name}")
        seen.add(name)
        source = entry.get("source")
        if source != f"plugins/cursor/{name}":
            _add(
                issues,
                root,
                path,
                "marketplace source does not match generated plugin",
            )
            continue
        source_path = root / source
        resolved = source_path.resolve()
        if (
            source_path.is_symlink()
            or not resolved.is_relative_to(root.resolve())
            or not resolved.is_dir()
        ):
            _add(issues, root, path, "marketplace source is missing or unsafe")
    if names != list(plugins):
        _add(
            issues,
            root,
            path,
            "marketplace plugin order does not match core manifest",
        )


def validate_cursor_plugins(root: Path) -> list[ValidationIssue]:
    root = root.resolve()
    issues: list[ValidationIssue] = []
    manifest = load_manifest(root)
    plugins = {
        name: manifest["plugins"][name]
        for name in platform_plugin_names(manifest, "cursor")
    }
    plugins_root = root / "plugins" / "cursor"
    if not plugins_root.is_dir():
        _add(issues, root, plugins_root, "missing generated Cursor plugins root")
    else:
        generated = {
            path.name
            for path in plugins_root.iterdir()
            if path.is_dir() and path.name != "__pycache__"
        }
        for name, expected in plugins.items():
            plugin_root = plugins_root / name
            if name not in generated:
                _add(
                    issues,
                    root,
                    plugins_root,
                    f"missing generated plugin '{name}'",
                )
            elif plugin_root.is_symlink():
                _add(
                    issues,
                    root,
                    plugin_root,
                    "plugin directory must not be a symlink",
                )
            else:
                _validate_plugin(root, plugin_root, expected, issues)
        for name in sorted(generated - set(plugins)):
            _add(
                issues,
                root,
                plugins_root / name,
                f"unexpected generated plugin '{name}'",
            )
    _validate_marketplace(root, plugins, issues)
    return sorted(issues, key=lambda issue: (issue.path.as_posix(), issue.message))
