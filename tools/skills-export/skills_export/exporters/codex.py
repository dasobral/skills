from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..manifest import (
    codex_adapter_dir,
    codex_plugins_dir,
    copy_skill,
    copy_tree,
    load_manifest,
    plugin_skill_names,
    repo_root,
)


COMPONENT_FIELDS = {"skills", "hooks", "mcpServers", "apps"}
PRESENTATION_FIELDS = ("interface", "homepage", "repository")
INTERFACE_PATH_FIELDS = {"composerIcon", "logo"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_OVERLAY_ENTRIES = {
    ".codex-plugin",
    "plugin.json",
    "skills",
    "hooks",
    "agents",
    "README.md",
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _validate_component_path(raw: object) -> None:
    if not isinstance(raw, str):
        raise ValueError("Codex component path must be a string")
    path = Path(raw)
    if (
        not raw.startswith("./")
        or path.is_absolute()
        or ".." in path.parts
    ):
        raise ValueError(f"Unsafe Codex component path: {raw!r}")


def _validate_existing_adapter_path(
    adapter: Path,
    raw: object,
    *,
    label: str,
) -> None:
    try:
        _validate_component_path(raw)
    except ValueError as exc:
        raise ValueError(f"Unsafe {label}: {raw!r}") from exc
    resolved = (adapter / str(raw)).resolve()
    if not resolved.is_relative_to(adapter.resolve()):
        raise ValueError(f"Unsafe {label}: path escapes adapter")
    if not resolved.is_file():
        raise ValueError(f"Invalid {label}: referenced file does not exist")


def _validate_overlay_interface(adapter: Path, overlay: dict[str, Any]) -> None:
    interface = overlay.get("interface")
    if interface is None:
        return
    if not isinstance(interface, dict):
        raise ValueError("Codex interface must be an object")
    for field in INTERFACE_PATH_FIELDS:
        if field in interface:
            _validate_existing_adapter_path(
                adapter,
                interface[field],
                label=f"interface.{field}",
            )
    if "screenshots" in interface:
        screenshots = interface["screenshots"]
        if not isinstance(screenshots, list) or not screenshots:
            raise ValueError("Codex interface.screenshots must be a non-empty list")
        for screenshot in screenshots:
            _validate_existing_adapter_path(
                adapter,
                screenshot,
                label="interface.screenshots",
            )


def _validate_repository_root(root: Path) -> None:
    if root.is_symlink():
        raise ValueError(f"Codex repository root must not be a symlink: {root}")
    if not root.is_dir():
        raise ValueError(f"Codex repository root does not exist: {root}")


def _assert_no_symlink_ancestors(root: Path, path: Path, *, label: str) -> None:
    root_absolute = root.absolute()
    path_absolute = path.absolute()
    try:
        relative = path_absolute.relative_to(root_absolute)
    except ValueError as exc:
        raise ValueError(f"{label} is outside repository root: {path}") from exc
    current = root_absolute
    if current.is_symlink():
        raise ValueError(f"{label} ancestor is a symlink: {current}")
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{label} ancestor is a symlink: {current}")


def _assemble_plugin_json(
    plugin_name: str,
    plugin_meta: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": plugin_name,
        "version": plugin_meta["version"],
        "description": plugin_meta["description"].strip(),
        "author": plugin_meta.get("_author", {"name": "Unknown"}),
        "license": plugin_meta.get("_license", "MIT"),
        "keywords": plugin_meta.get("keywords", []),
        "skills": "./skills/",
    }
    for key in PRESENTATION_FIELDS:
        if key in overlay:
            result[key] = overlay[key]
    for key in ("mcpServers", "apps"):
        if key in overlay:
            result[key] = overlay[key]
    if plugin_meta.get("_has_hooks"):
        result["hooks"] = "./hooks/hooks.json"
    return result


def _assert_safe_source_tree(
    source: Path,
    *,
    repository_root: Path,
    container: Path,
    label: str,
) -> None:
    _assert_no_symlink_ancestors(repository_root, container, label=label)
    _assert_no_symlink_ancestors(repository_root, source, label=label)
    if not source.exists() and not source.is_symlink():
        return
    if source.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {source}")
    resolved_container = container.resolve()
    if not source.resolve().is_relative_to(resolved_container):
        raise ValueError(f"{label} escapes its source root: {source}")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"{label} contains a symlink: {path}")
        if not path.resolve().is_relative_to(resolved_container):
            raise ValueError(f"{label} escapes its source root: {path}")


def _safe_output_path(
    repository_root: Path,
    output_root: Path,
    plugin_name: str,
) -> Path:
    resolved_repository = repository_root.resolve()
    if not output_root.resolve().is_relative_to(resolved_repository):
        raise ValueError(
            f"Codex output root must stay inside repository: {output_root}"
        )
    if output_root.is_symlink():
        raise ValueError(f"Codex output root must not be a symlink: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    resolved_root = output_root.resolve()
    plugin_out = output_root / plugin_name
    if plugin_out.is_symlink():
        raise ValueError(f"Codex output target must not be a symlink: {plugin_out}")
    if not plugin_out.resolve().is_relative_to(resolved_root):
        raise ValueError(f"Codex output target escapes output root: {plugin_out}")
    return plugin_out


def _copy_overlay_assets(adapter: Path, plugin_out: Path) -> None:
    if not adapter.is_dir():
        return
    for source in sorted(adapter.iterdir(), key=lambda path: path.name):
        if source.name in RESERVED_OVERLAY_ENTRIES:
            continue
        destination = plugin_out / source.name
        if source.is_dir():
            copy_tree(source, destination)
        elif source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _generated_readme(
    plugin_name: str,
    plugin_meta: dict[str, Any],
    plugin_out: Path,
) -> str:
    skills = sorted(path.name for path in (plugin_out / "skills").iterdir())
    agents_dir = plugin_out / "agents"
    agents = (
        sorted(path.name for path in agents_dir.glob("*.toml"))
        if agents_dir.is_dir()
        else []
    )
    hooks = ["hooks/hooks.json"] if (plugin_out / "hooks/hooks.json").is_file() else []

    def section(title: str, values: list[str]) -> str:
        items = "\n".join(f"- `{value}`" for value in values) or "- None"
        return f"## {title}\n\n{items}\n"

    return (
        f"# {plugin_meta['display_name']}\n\n"
        f"{plugin_meta['description'].strip()}\n\n"
        f"Native Codex plugin `{plugin_name}` generated from portable core skills "
        "and its Codex adapter.\n\n"
        + section("Skills", skills)
        + "\n"
        + section("Agent templates", agents)
        + "\n"
        + section("Hooks", hooks)
        + "\n## Data handling\n\n"
        "Review bundled hooks before enabling them. Agent templates are not "
        "installed automatically.\n"
    )


def export_codex_plugin(
    root: Path,
    plugin_name: str,
    output_root: Path,
    *,
    clean: bool = True,
) -> Path:
    _validate_repository_root(root)
    if not isinstance(plugin_name, str) or not NAME_RE.fullmatch(plugin_name):
        raise ValueError(f"Invalid Codex plugin name: {plugin_name!r}")
    manifest = load_manifest(root)
    if plugin_name not in manifest["plugins"]:
        raise KeyError(f"Unknown plugin: {plugin_name}")
    plugin_meta = dict(manifest["plugins"][plugin_name])
    plugin_meta["_author"] = manifest.get("author", {"name": "Unknown"})
    plugin_meta["_license"] = manifest.get("license", "MIT")
    adapter = codex_adapter_dir(root, plugin_name)
    adapters_root = root / "adapters" / "codex"
    _assert_safe_source_tree(
        adapter,
        repository_root=root,
        container=adapters_root,
        label="Codex adapter",
    )

    skill_names = plugin_skill_names(manifest, plugin_name)
    skills_root = root / "core" / "skills"
    for skill_name in skill_names:
        if not isinstance(skill_name, str) or not NAME_RE.fullmatch(skill_name):
            raise ValueError(f"Invalid core skill name: {skill_name!r}")
        skill_source = skills_root / skill_name
        if not skill_source.is_dir():
            raise FileNotFoundError(f"Missing core skill: {skill_source}")
        _assert_safe_source_tree(
            skill_source,
            repository_root=root,
            container=skills_root,
            label="Core skill source",
        )

    overlay_path = adapter / ".codex-plugin" / "plugin.json"
    overlay = (
        json.loads(overlay_path.read_text(encoding="utf-8"))
        if overlay_path.is_file()
        else {}
    )
    if not isinstance(overlay, dict):
        raise ValueError(f"Codex overlay manifest must be an object: {overlay_path}")
    for key in COMPONENT_FIELDS & overlay.keys():
        _validate_component_path(overlay[key])
    for key in ("mcpServers", "apps"):
        if key in overlay:
            _validate_existing_adapter_path(
                adapter,
                overlay[key],
                label=key,
            )
            component = adapter / str(overlay[key])
            try:
                component_data = json.loads(component.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid {key} component JSON: {exc}") from exc
            if not isinstance(component_data, dict):
                raise ValueError(f"{key} component must contain a JSON object")
    _validate_overlay_interface(adapter, overlay)

    shared = (
        codex_adapter_dir(root, "_shared")
        / "skills"
        / "install-plugin-agents"
    )
    if (adapter / "agents").is_dir():
        if not shared.is_dir():
            raise FileNotFoundError(
                "Codex plugins with agents require the shared "
                "install-plugin-agents skill"
            )
        _assert_safe_source_tree(
            shared,
            repository_root=root,
            container=codex_adapter_dir(root, "_shared"),
            label="Shared Codex setup skill",
        )
        installer_module = (
            root
            / "tools"
            / "skills-export"
            / "skills_export"
            / "agent_installer.py"
        )
        if not installer_module.is_file() or installer_module.is_symlink():
            raise FileNotFoundError(
                f"Missing safe Codex agent installer module: {installer_module}"
            )

    plugin_out = _safe_output_path(root, output_root, plugin_name)
    if clean and plugin_out.exists():
        shutil.rmtree(plugin_out)
    plugin_out.mkdir(parents=True, exist_ok=True)

    skills_out = plugin_out / "skills"
    skills_out.mkdir()
    for skill in skill_names:
        copy_skill(root, skill, skills_out / skill)

    adapter_skills = adapter / "skills"
    if adapter_skills.is_dir():
        for source in sorted(adapter_skills.iterdir(), key=lambda path: path.name):
            if source.is_dir():
                copy_tree(source, skills_out / source.name)

    for component in ("hooks", "agents"):
        source = adapter / component
        if source.is_dir():
            copy_tree(source, plugin_out / component)
    _copy_overlay_assets(adapter, plugin_out)

    if (plugin_out / "agents").is_dir():
        installed_skill = skills_out / "install-plugin-agents"
        copy_tree(shared, installed_skill)
        scripts = installed_skill / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        shutil.copy2(installer_module, scripts / "agent_installer.py")

    if (plugin_out / "hooks" / "hooks.json").is_file():
        plugin_meta["_has_hooks"] = True
    plugin_json = _assemble_plugin_json(plugin_name, plugin_meta, overlay)
    _write_json(plugin_out / ".codex-plugin" / "plugin.json", plugin_json)
    (plugin_out / "README.md").write_text(
        _generated_readme(plugin_name, plugin_meta, plugin_out),
        encoding="utf-8",
    )
    return plugin_out


def export_codex_marketplace(root: Path) -> Path:
    _validate_repository_root(root)
    manifest = load_manifest(root)
    for name in manifest["plugins"]:
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise ValueError(f"Invalid Codex plugin name: {name!r}")
    category_names = {
        "developer-tools": "Developer Tools",
        "productivity": "Productivity",
        "security": "Security",
        "research": "Research",
    }
    entries = [
        {
            "name": name,
            "source": {
                "source": "local",
                "path": f"./plugins/codex/{name}",
            },
            "policy": {
                "installation": "AVAILABLE",
                "authentication": "ON_INSTALL",
            },
            "category": category_names.get(
                meta.get("category", ""),
                str(meta.get("category", "Other")).replace("-", " ").title(),
            ),
            "interface": {"displayName": meta["display_name"]},
        }
        for name, meta in manifest["plugins"].items()
    ]
    marketplace = {
        "name": manifest.get("marketplace", {}).get("name", "skills"),
        "interface": {"displayName": "Dasobral Skills"},
        "plugins": entries,
    }
    destination = root / ".agents" / "plugins" / "marketplace.json"
    for parent in (root / ".agents", destination.parent):
        if parent.is_symlink():
            raise ValueError(
                f"Codex marketplace parent must not be a symlink: {parent}"
            )
        parent.mkdir(exist_ok=True)
        if not parent.resolve().is_relative_to(root.resolve()):
            raise ValueError(
                f"Codex marketplace parent escapes repository: {parent}"
            )
    if destination.is_symlink():
        raise ValueError(
            f"Codex marketplace output must not be a symlink: {destination}"
        )
    _write_json(destination, marketplace)
    return destination


def export_codex_plugins(
    root: Path,
    output_root: Path | None = None,
    *,
    plugins: list[str] | None = None,
    clean: bool = True,
) -> list[Path]:
    _validate_repository_root(root)
    output_root = output_root or codex_plugins_dir(root)
    manifest = load_manifest(root)
    names = plugins or list(manifest["plugins"])
    for name in names:
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise ValueError(f"Invalid Codex plugin name: {name!r}")
    _safe_output_path(root, output_root, names[0] if names else "plugin")

    if clean and plugins is None:
        staging = Path(
            tempfile.mkdtemp(
                prefix=".codex-export-",
                dir=output_root.parent,
            )
        )
        try:
            for name in names:
                export_codex_plugin(root, name, staging, clean=False)
            if output_root.exists():
                if output_root.is_symlink():
                    raise ValueError(
                        f"Codex output root must not be a symlink: {output_root}"
                    )
                shutil.rmtree(output_root)
            os.replace(staging, output_root)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        results = [output_root / name for name in names]
    else:
        results = [
            export_codex_plugin(root, name, output_root, clean=clean)
            for name in names
        ]
    export_codex_marketplace(root)
    return results


def export_codex_flat(root: Path, output_dir: Path, *, clean: bool = True) -> Path:
    _validate_repository_root(root)
    manifest = load_manifest(root)
    skills_root = root / "core" / "skills"
    seen: set[str] = set()
    skill_names: list[str] = []
    for plugin in manifest["plugins"].values():
        for skill in plugin["skills"]:
            if not isinstance(skill, str) or not NAME_RE.fullmatch(skill):
                raise ValueError(f"Invalid core skill name: {skill!r}")
            if skill in seen:
                continue
            seen.add(skill)
            skill_names.append(skill)
            source = skills_root / skill
            if not source.is_dir():
                raise FileNotFoundError(f"Missing core skill: {source}")
            _assert_safe_source_tree(
                source,
                repository_root=root,
                container=skills_root,
                label="Core skill source",
            )
    references = root / "core" / "references"
    _assert_safe_source_tree(
        references,
        repository_root=root,
        container=root / "core",
        label="Core references source",
    )
    if output_dir.is_symlink():
        raise ValueError(f"Codex flat output must not be a symlink: {output_dir}")
    flat = output_dir / "skills"
    if flat.is_symlink():
        raise ValueError(f"Codex flat output must not be a symlink: {flat}")
    if not flat.resolve().is_relative_to(output_dir.resolve()):
        raise ValueError(f"Codex flat output escapes destination: {flat}")
    if clean and flat.exists():
        shutil.rmtree(flat)
    flat.mkdir(parents=True, exist_ok=True)

    for skill in skill_names:
        copy_skill(root, skill, flat / skill)

    (output_dir / "README.md").write_text(
        """# Codex skills (flat export)

Copy into `~/.codex/skills/` or project `.agents/skills/`:

```bash
cp -r skills/* ~/.codex/skills/
# or
cp -r skills/* .agents/skills/
```
""",
        encoding="utf-8",
    )
    return flat


def export_codex(
    root: Path | None = None,
    output_dir: Path | None = None,
    *,
    flat_output_dir: Path | None = None,
    native_output_dir: Path | None = None,
    plugins: list[str] | None = None,
    flat: bool = True,
    native: bool = False,
    bundles: bool | None = None,
) -> list[Path]:
    root = root or repo_root()
    if bundles is not None:
        raise ValueError(
            "legacy Codex bundles were removed; omit 'bundles' and use "
            "native_output_dir for native plugins"
        )
    if flat_output_dir is not None and output_dir is not None:
        raise ValueError("Use output_dir or flat_output_dir, not both")
    flat_output_dir = flat_output_dir or output_dir or root / "dist" / "codex"
    native = native or native_output_dir is not None
    if not flat and not native:
        raise ValueError("Codex export requested no artifacts")
    results: list[Path] = []

    if flat:
        results.append(export_codex_flat(root, flat_output_dir))

    refs_out = flat_output_dir / "references"
    refs_src = root / "core" / "references"
    if flat and refs_src.is_dir():
        if refs_out.exists():
            shutil.rmtree(refs_out)
        shutil.copytree(refs_src, refs_out)

    if native:
        if native_output_dir is None:
            raise ValueError("native_output_dir is required for native Codex export")
        results.extend(
            export_codex_plugins(root, native_output_dir, plugins=plugins)
        )

    return results
