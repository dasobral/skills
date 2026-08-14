"""Commit-friendly Agent Plugins 1.0 packages: plugin.json + skill symlinks."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .manifest import load_manifest, plugin_skill_names, skills_dir

AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
_NATIVE_PLUGIN_DIRS = {"cursor", "claude", "codex"}


def _schema() -> dict[str, Any]:
    path = Path(__file__).parent / "schemas" / "plugin.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def portable_plugins_dir(root: Path) -> Path:
    return root / "plugins"


def portable_plugin_manifest(
    plugin_name: str,
    meta: dict[str, Any],
    root_manifest: dict[str, Any],
) -> dict[str, Any]:
    author = root_manifest.get("author", {"name": "Unknown"})
    if not isinstance(author, dict):
        author = {"name": str(author)}
    author_out = {
        key: author[key]
        for key in ("name", "email", "url")
        if author.get(key)
    }
    data: dict[str, Any] = {
        "$schema": AGENT_PLUGINS_SCHEMA,
        "name": plugin_name,
        "version": str(meta.get("version", "0.1.0")),
        "description": str(meta.get("description", "")).strip(),
        "license": root_manifest.get("license", "MIT"),
        "keywords": list(meta.get("keywords") or []),
    }
    if author_out:
        data["author"] = author_out
    return data


def _replace_symlink(dest: Path, target: Path) -> None:
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.exists():
        shutil.rmtree(dest)
    dest.symlink_to(target, target_is_directory=True)


def export_portable_plugin(root: Path, plugin_name: str) -> Path:
    """Write plugins/<name>/plugin.json and skills/<skill> → ../../../skills/<skill>."""
    manifest = load_manifest(root)
    meta = manifest["plugins"][plugin_name]
    plugin_dir = portable_plugins_dir(root) / plugin_name
    skills_out = plugin_dir / "skills"
    skills_out.mkdir(parents=True, exist_ok=True)

    plugin_json = portable_plugin_manifest(plugin_name, meta, manifest)
    Draft202012Validator(_schema()).validate(plugin_json)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(plugin_json, indent=2) + "\n",
        encoding="utf-8",
    )

    wanted = set(plugin_skill_names(manifest, plugin_name))
    for skill in sorted(wanted):
        src = skills_dir(root) / skill
        if not (src / "SKILL.md").is_file():
            raise FileNotFoundError(f"missing portable skill '{skill}'")
        _replace_symlink(skills_out / skill, Path("../../../skills") / skill)

    for child in list(skills_out.iterdir()):
        if child.name not in wanted:
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)

    return plugin_dir


def export_portable_all(root: Path) -> list[Path]:
    manifest = load_manifest(root)
    plugins_root = portable_plugins_dir(root)
    plugins_root.mkdir(parents=True, exist_ok=True)
    results = [
        export_portable_plugin(root, name) for name in manifest["plugins"]
    ]
    wanted = set(manifest["plugins"]) | _NATIVE_PLUGIN_DIRS
    for child in list(plugins_root.iterdir()):
        if child.is_dir() and child.name not in wanted:
            shutil.rmtree(child)
    return results


def validate_portable_plugins(root: Path) -> list[str]:
    """Return errors for committed Agent Plugins packages (empty if none yet)."""
    manifest = load_manifest(root)
    plugins_root = portable_plugins_dir(root)
    errors: list[str] = []
    schema = _schema()
    validator = Draft202012Validator(schema)

    for name, meta in manifest["plugins"].items():
        plugin_dir = plugins_root / name
        plugin_json_path = plugin_dir / "plugin.json"
        if not plugin_json_path.is_file():
            errors.append(f"portable plugin '{name}': missing plugin.json")
            continue
        try:
            data = json.loads(plugin_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"portable plugin '{name}': invalid JSON ({exc})")
            continue
        schema_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        for err in schema_errors:
            loc = ".".join(str(p) for p in err.path) or "$"
            errors.append(f"portable plugin '{name}': {loc}: {err.message}")
        if data.get("name") != name:
            errors.append(
                f"portable plugin '{name}': plugin.json name '{data.get('name')}' must match directory"
            )
        expected_version = str(meta.get("version", ""))
        if expected_version and data.get("version") != expected_version:
            errors.append(
                f"portable plugin '{name}': version '{data.get('version')}' != manifest '{expected_version}'"
            )
        for skill in plugin_skill_names(manifest, name):
            link = plugin_dir / "skills" / skill
            skill_md = link / "SKILL.md"
            if not skill_md.is_file():
                errors.append(
                    f"portable plugin '{name}': skill '{skill}' missing or broken link"
                )
    return errors
