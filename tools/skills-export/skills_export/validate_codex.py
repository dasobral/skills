from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
PLUGIN_ROOT_PATH_RE = re.compile(r"\$\{PLUGIN_ROOT\}/([^\s\"']+)")
COMPONENT_FIELDS = ("skills", "hooks", "mcpServers", "apps")
HOOK_EVENTS = {
    "SessionStart",
    "SubagentStart",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PostCompact",
    "PreCompact",
    "UserPromptSubmit",
    "SubagentStop",
    "Stop",
}
SAFE_HOOK_EXECUTABLES = {
    "py",
    "python",
    "python3",
    "bash",
    "sh",
    "node",
    "/usr/bin/python",
    "/usr/bin/python3",
    "/bin/bash",
    "/bin/sh",
    "/usr/bin/node",
}
INSTALLATION_POLICIES = {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
AUTHENTICATION_POLICIES = {"ON_INSTALL", "ON_USE"}
INTERFACE_PATH_FIELDS = {"composerIcon", "logo"}


def _marketplace_category(value: object) -> str:
    categories = {
        "developer-tools": "Developer Tools",
        "productivity": "Productivity",
        "security": "Security",
        "research": "Research",
    }
    raw = str(value or "Other")
    return categories.get(raw, raw.replace("-", " ").title())


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str


def _reported_path(root: Path, path: Path) -> Path:
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
    issues.append(ValidationIssue(_reported_path(root, path), message))


def _safe_declared_path(
    *,
    root: Path,
    container: Path,
    owner: Path,
    raw: object,
    label: str,
    container_label: str,
    issues: list[ValidationIssue],
) -> Path | None:
    if not isinstance(raw, str):
        _add(issues, root, owner, f"{label} must be a string path")
        return None
    declared = Path(raw)
    if not raw.startswith("./"):
        _add(issues, root, owner, f"{label} must begin with './'")
        return None
    if declared.is_absolute():
        _add(issues, root, owner, f"{label} must be relative")
        return None
    if ".." in declared.parts:
        _add(issues, root, owner, f"{label} must not contain '..'")
        return None
    resolved = (container / declared).resolve()
    if not resolved.is_relative_to(container.resolve()):
        _add(issues, root, owner, f"{label} escapes {container_label}")
        return None
    current = container
    for part in declared.parts:
        if part in ("", "."):
            continue
        current /= part
        if current.is_symlink():
            _add(issues, root, owner, f"{label} must not traverse a symlink")
            return None
    if not resolved.exists():
        _add(issues, root, owner, f"{label} referenced path does not exist")
        return None
    return resolved


def _validate_interface_paths(
    *,
    root: Path,
    container: Path,
    owner: Path,
    interface: object,
    label: str,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(interface, dict):
        _add(issues, root, owner, f"{label} must be an object")
        return
    values: list[tuple[str, object]] = [
        (field, interface[field])
        for field in INTERFACE_PATH_FIELDS
        if field in interface
    ]
    if "screenshots" in interface:
        screenshots = interface["screenshots"]
        if not isinstance(screenshots, list) or not screenshots:
            _add(
                issues,
                root,
                owner,
                f"{label}.screenshots must be a non-empty list",
            )
        else:
            values.extend(("screenshots", value) for value in screenshots)
    for field, raw in values:
        resolved = _safe_declared_path(
            root=root,
            container=container,
            owner=owner,
            raw=raw,
            label=f"{label}.{field}",
            container_label=container.name,
            issues=issues,
        )
        if resolved is not None and not resolved.is_file():
            _add(
                issues,
                root,
                owner,
                f"{label}.{field} must reference a file",
            )


def _validate_no_symlink_ancestors(
    root: Path,
    path: Path,
    *,
    label: str,
    issues: list[ValidationIssue],
) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        _add(issues, root, path, f"{label} is outside repository root")
        return False
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            _add(issues, root, current, f"{label} ancestor is a symlink")
            return False
    return True


def _validate_skills(
    root: Path,
    skills_dir: Path,
    issues: list[ValidationIssue],
) -> None:
    if not skills_dir.is_dir():
        _add(issues, root, skills_dir, "skills component must be a directory")
        return
    for skill_dir in sorted(skills_dir.iterdir(), key=lambda path: path.name):
        if not skill_dir.is_dir():
            continue
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


def _validate_agents(
    root: Path,
    plugin_root: Path,
    issues: list[ValidationIssue],
) -> None:
    agents_dir = plugin_root / "agents"
    if not agents_dir.exists():
        return
    if not agents_dir.is_dir():
        _add(issues, root, agents_dir, "agents must be a directory")
        return
    for agent in sorted(agents_dir.glob("*.toml")):
        try:
            data = tomllib.loads(agent.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            _add(issues, root, agent, f"invalid TOML: {exc}")
            continue
        for key in ("name", "description", "developer_instructions"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                _add(issues, root, agent, f"missing required key '{key}'")


def _validate_json_component(
    root: Path,
    path: Path,
    *,
    field: str,
    issues: list[ValidationIssue],
) -> None:
    if not path.is_file():
        _add(issues, root, path, f"{field} component must be a file")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(issues, root, path, f"invalid {field} component JSON: {exc}")
        return
    if not isinstance(data, dict):
        _add(issues, root, path, f"{field} component must contain a JSON object")


def _validate_hook_command(
    root: Path,
    plugin_root: Path,
    hooks_path: Path,
    command: object,
    issues: list[ValidationIssue],
    *,
    field_name: str = "command",
    windows: bool = False,
) -> None:
    label = "hook command" if field_name == "command" else f"hook {field_name}"
    if not isinstance(command, str) or not command.strip():
        _add(issues, root, hooks_path, f"{label} must be a non-empty string")
        return
    normalized = command
    if windows:
        normalized = normalized.replace("%PLUGIN_ROOT%", "${PLUGIN_ROOT}")
        normalized = normalized.replace("\\", "/")
    if any(token in normalized for token in ("$(", "`", ";", "\n", "&&", "||", "|", ">", "<")):
        _add(issues, root, hooks_path, f"{label} contains unsafe shell expansion")
        return
    try:
        operands = shlex.split(normalized)
    except ValueError as exc:
        _add(issues, root, hooks_path, f"invalid {label} quoting: {exc}")
        return
    if not operands:
        _add(issues, root, hooks_path, f"{label} must not be empty")
        return
    executable = operands[0]
    plugin_executable = executable.startswith("${PLUGIN_ROOT}/")
    if not plugin_executable and executable not in SAFE_HOOK_EXECUTABLES:
        executable_label = (
            "hook executable"
            if field_name == "command"
            else f"hook {field_name} executable"
        )
        _add(issues, root, hooks_path, f"unsafe {executable_label}: {executable}")

    matches = list(PLUGIN_ROOT_PATH_RE.finditer(normalized))
    if not matches:
        _add(
            issues,
            root,
            hooks_path,
            f"{label} must reference a bundled plugin script",
        )
    for match in matches:
        suffix = match.group(1)
        relative = Path(suffix)
        if ".." in relative.parts:
            _add(
                issues,
                root,
                hooks_path,
                "hook script path must not contain '..'",
            )
            continue
        script = (plugin_root / relative).resolve()
        if not script.is_relative_to(plugin_root.resolve()):
            _add(issues, root, hooks_path, "hook script escapes plugin root")
        elif not script.is_file():
            _add(
                issues,
                root,
                hooks_path,
                f"hook script does not exist: {suffix}",
            )
        elif script.is_symlink():
            _add(issues, root, hooks_path, "hook script must not be a symlink")

    for operand in operands[1:]:
        if operand.startswith("${PLUGIN_ROOT}/"):
            continue
        if "${" in operand or "$" in operand:
            _add(issues, root, hooks_path, "hook command contains unsafe expansion")
        elif (
            operand.startswith(("/", "./", "../", "~"))
            or "://" in operand
            or re.match(r"^[A-Za-z]:/", operand)
        ):
            _add(
                issues,
                root,
                hooks_path,
                f"unsafe external {label} operand: {operand}",
            )


def _validate_hooks(
    root: Path,
    plugin_root: Path,
    hooks_path: Path,
    issues: list[ValidationIssue],
) -> None:
    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(issues, root, hooks_path, f"invalid hook JSON: {exc}")
        return
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        _add(issues, root, hooks_path, "hook JSON must contain a hooks object")
        return
    if set(data) != {"hooks"}:
        _add(issues, root, hooks_path, "hook JSON may only contain 'hooks'")
    for event, groups in data["hooks"].items():
        if event not in HOOK_EVENTS:
            _add(issues, root, hooks_path, f"unsupported hook event: {event}")
        if not isinstance(groups, list):
            _add(
                issues,
                root,
                hooks_path,
                "each hook event must map to a list",
            )
            continue
        for group in groups:
            if not isinstance(group, dict):
                _add(issues, root, hooks_path, "matcher group must be an object")
                continue
            handlers = group.get("hooks")
            if not isinstance(handlers, list) or not handlers:
                _add(
                    issues,
                    root,
                    hooks_path,
                    "matcher group must contain a hooks list",
                )
                continue
            if set(group) - {"matcher", "hooks"}:
                _add(
                    issues,
                    root,
                    hooks_path,
                    "matcher group contains unsupported fields",
                )
            matcher = group.get("matcher")
            if matcher is not None:
                if not isinstance(matcher, str):
                    _add(issues, root, hooks_path, "matcher must be a string")
                else:
                    try:
                        re.compile(matcher)
                    except re.error as exc:
                        _add(
                            issues,
                            root,
                            hooks_path,
                            f"invalid matcher regex: {exc}",
                        )
            for handler in handlers:
                if not isinstance(handler, dict):
                    _add(issues, root, hooks_path, "hook handler must be an object")
                    continue
                if handler.get("type") != "command":
                    _add(
                        issues,
                        root,
                        hooks_path,
                        "hook handler type must be 'command'",
                    )
                    continue
                allowed = {
                    "type",
                    "command",
                    "commandWindows",
                    "timeout",
                    "statusMessage",
                    "async",
                }
                if set(handler) - allowed:
                    _add(
                        issues,
                        root,
                        hooks_path,
                        "command handler contains unsupported fields",
                    )
                timeout = handler.get("timeout")
                if timeout is not None and (
                    not isinstance(timeout, (int, float)) or timeout <= 0
                ):
                    _add(
                        issues,
                        root,
                        hooks_path,
                        "hook timeout must be a positive number",
                    )
                status = handler.get("statusMessage")
                if status is not None and not isinstance(status, str):
                    _add(
                        issues,
                        root,
                        hooks_path,
                        "hook statusMessage must be a string",
                    )
                if handler.get("async") is True:
                    _add(
                        issues,
                        root,
                        hooks_path,
                        "asynchronous command hooks are unsupported",
                    )
                _validate_hook_command(
                    root,
                    plugin_root,
                    hooks_path,
                    handler.get("command"),
                    issues,
                )
                if "commandWindows" in handler:
                    _validate_hook_command(
                        root,
                        plugin_root,
                        hooks_path,
                        handler.get("commandWindows"),
                        issues,
                        field_name="commandWindows",
                        windows=True,
                    )


def _validate_plugin(
    root: Path,
    plugin_root: Path,
    expected: dict[str, Any] | None,
    issues: list[ValidationIssue],
) -> None:
    for path in plugin_root.rglob("*"):
        if path.is_symlink():
            _add(
                issues,
                root,
                path,
                "plugin tree must not contain symlinks",
            )
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        _add(
            issues,
            root,
            plugin_root,
            "missing .codex-plugin/plugin.json",
        )
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(issues, root, manifest_path, f"invalid JSON: {exc}")
        return
    if not isinstance(manifest, dict):
        _add(issues, root, manifest_path, "plugin manifest must be an object")
        return
    name = manifest.get("name")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        _add(
            issues,
            root,
            manifest_path,
            "plugin name must be lowercase kebab-case",
        )
    elif name != plugin_root.name:
        _add(
            issues,
            root,
            manifest_path,
            "plugin name must match its directory",
        )
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        _add(
            issues,
            root,
            manifest_path,
            "plugin version must be a semantic version",
        )
    description = manifest.get("description")
    if not isinstance(description, str) or not description.strip():
        _add(
            issues,
            root,
            manifest_path,
            "plugin must have a non-empty description",
        )
    author = manifest.get("author")
    if not isinstance(author, dict):
        _add(issues, root, manifest_path, "plugin author must be an object")
    elif not isinstance(author.get("name"), str) or not author["name"].strip():
        _add(
            issues,
            root,
            manifest_path,
            "plugin author.name must be a non-empty string",
        )
    license_name = manifest.get("license")
    if not isinstance(license_name, str) or not license_name.strip():
        _add(
            issues,
            root,
            manifest_path,
            "plugin license must be a non-empty string",
        )
    keywords = manifest.get("keywords")
    if not isinstance(keywords, list):
        _add(issues, root, manifest_path, "plugin keywords must be a list")
    elif any(not isinstance(keyword, str) for keyword in keywords):
        _add(
            issues,
            root,
            manifest_path,
            "plugin keywords must contain strings",
        )
    if expected is not None:
        for key in ("version", "keywords"):
            if manifest.get(key) != expected.get(key, [] if key == "keywords" else None):
                _add(
                    issues,
                    root,
                    manifest_path,
                    f"plugin {key} does not match core manifest",
                )
        if str(manifest.get("description", "")).strip() != str(
            expected.get("description", "")
        ).strip():
            _add(
                issues,
                root,
                manifest_path,
                "plugin description does not match core manifest",
            )
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        _add(issues, root, manifest_path, "plugin interface must be an object")
    else:
        display_name = interface.get("displayName")
        if not isinstance(display_name, str) or not display_name.strip():
            _add(
                issues,
                root,
                manifest_path,
                "plugin interface.displayName must be a non-empty string",
            )
        elif expected is not None and display_name != expected.get("display_name"):
            _add(
                issues,
                root,
                manifest_path,
                "plugin interface.displayName does not match core manifest",
            )
        _validate_interface_paths(
            root=root,
            container=plugin_root,
            owner=manifest_path,
            interface=interface,
            label="interface",
            issues=issues,
        )

    resolved_components: dict[str, Path] = {}
    for field in COMPONENT_FIELDS:
        if field not in manifest:
            continue
        resolved = _safe_declared_path(
            root=root,
            container=plugin_root,
            owner=manifest_path,
            raw=manifest[field],
            label=f"component path '{field}'",
            container_label="plugin root",
            issues=issues,
        )
        if resolved is not None:
            resolved_components[field] = resolved
    if "skills" not in manifest:
        _add(issues, root, manifest_path, "plugin manifest is missing skills")
    elif "skills" in resolved_components:
        _validate_skills(root, resolved_components["skills"], issues)
        if expected is not None:
            generated_skills = {
                path.name
                for path in resolved_components["skills"].iterdir()
                if path.is_dir()
            }
            for skill in expected.get("skills", []):
                if skill not in generated_skills:
                    _add(
                        issues,
                        root,
                        resolved_components["skills"],
                        f"missing generated core skill '{skill}'",
                    )
    if "hooks" in resolved_components:
        _validate_hooks(
            root,
            plugin_root,
            resolved_components["hooks"],
            issues,
        )
    for field in ("mcpServers", "apps"):
        if field in resolved_components:
            _validate_json_component(
                root,
                resolved_components[field],
                field=field,
                issues=issues,
            )
    _validate_agents(root, plugin_root, issues)


def _validate_marketplace(
    root: Path,
    core_plugins: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    path = root / ".agents" / "plugins" / "marketplace.json"
    if not _validate_no_symlink_ancestors(
        root,
        path,
        label="marketplace metadata",
        issues=issues,
    ):
        return
    if not path.exists():
        _add(issues, root, path, "missing generated Codex marketplace")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(issues, root, path, f"invalid marketplace JSON: {exc}")
        return
    if not isinstance(data, dict) or not isinstance(data.get("plugins"), list):
        _add(issues, root, path, "marketplace must contain a plugins list")
        return
    seen: set[str] = set()
    ordered_names: list[str] = []
    for entry in data["plugins"]:
        if not isinstance(entry, dict):
            _add(issues, root, path, "marketplace plugin must be an object")
            continue
        name = entry.get("name")
        if name in seen:
            _add(
                issues,
                root,
                path,
                f"duplicate marketplace plugin: {name}",
            )
        if isinstance(name, str):
            seen.add(name)
            ordered_names.append(name)
        expected = core_plugins.get(name) if isinstance(name, str) else None
        if isinstance(name, str) and expected is None:
            _add(
                issues,
                root,
                path,
                f"unexpected marketplace plugin '{name}'",
            )
        source = entry.get("source")
        if not isinstance(source, dict) or source.get("source") != "local":
            _add(
                issues,
                root,
                path,
                "marketplace source.source must equal 'local'",
            )
        raw = source.get("path") if isinstance(source, dict) else None
        resolved_source = _safe_declared_path(
            root=root,
            container=root,
            owner=path,
            raw=raw,
            label="marketplace source",
            container_label="repository root",
            issues=issues,
        )
        if isinstance(name, str) and raw != f"./plugins/codex/{name}":
            _add(
                issues,
                root,
                path,
                "marketplace source path does not match core manifest",
            )
        policy = entry.get("policy")
        if not isinstance(policy, dict):
            _add(issues, root, path, "marketplace policy must be an object")
        else:
            if policy.get("installation") not in INSTALLATION_POLICIES:
                _add(
                    issues,
                    root,
                    path,
                    "invalid policy.installation",
                )
            if policy.get("authentication") not in AUTHENTICATION_POLICIES:
                _add(
                    issues,
                    root,
                    path,
                    "invalid policy.authentication",
                )
        category = entry.get("category")
        if not isinstance(category, str) or not category.strip():
            _add(
                issues,
                root,
                path,
                "marketplace category must be a non-empty string",
            )
        elif expected is not None and category != _marketplace_category(
            expected.get("category")
        ):
            _add(
                issues,
                root,
                path,
                "marketplace category does not match core manifest",
            )
        interface = entry.get("interface")
        display_name = (
            interface.get("displayName") if isinstance(interface, dict) else None
        )
        if expected is not None and display_name != expected.get("display_name"):
            _add(
                issues,
                root,
                path,
                "marketplace displayName does not match core manifest",
            )
        if interface is not None and resolved_source is not None:
            _validate_interface_paths(
                root=root,
                container=resolved_source,
                owner=path,
                interface=interface,
                label="marketplace interface",
                issues=issues,
            )
    for name in core_plugins:
        if name not in seen:
            _add(
                issues,
                root,
                path,
                f"missing marketplace plugin '{name}'",
            )
    if ordered_names != list(core_plugins):
        _add(
            issues,
            root,
            path,
            "marketplace plugin order does not match core manifest",
        )
    top_interface = data.get("interface")
    if top_interface is not None:
        _validate_interface_paths(
            root=root,
            container=root,
            owner=path,
            interface=top_interface,
            label="marketplace interface",
            issues=issues,
        )


def validate_codex_plugins(root: Path) -> list[ValidationIssue]:
    root = root.resolve()
    issues: list[ValidationIssue] = []
    core_manifest_path = root / "core" / "manifest.yaml"
    try:
        core_manifest = yaml.safe_load(
            core_manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        _add(issues, root, core_manifest_path, f"invalid core manifest: {exc}")
        core_manifest = {}
    core_plugins = (
        core_manifest.get("plugins", {})
        if isinstance(core_manifest, dict)
        and isinstance(core_manifest.get("plugins", {}), dict)
        else {}
    )
    plugins_root = root / "plugins" / "codex"
    generated_names: set[str] = set()
    if not plugins_root.is_dir():
        _add(
            issues,
            root,
            plugins_root,
            "missing generated Codex plugins root",
        )
    else:
        for plugin_root in sorted(
            (path for path in plugins_root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        ):
            generated_names.add(plugin_root.name)
            if plugin_root.is_symlink():
                _add(
                    issues,
                    root,
                    plugin_root,
                    "plugin directory must not be a symlink",
                )
                continue
            if not plugin_root.resolve().is_relative_to(plugins_root.resolve()):
                _add(
                    issues,
                    root,
                    plugin_root,
                    "plugin directory escapes Codex plugin root",
                )
                continue
            _validate_plugin(
                root,
                plugin_root,
                core_plugins.get(plugin_root.name),
                issues,
            )
        for name in core_plugins:
            if name not in generated_names:
                _add(
                    issues,
                    root,
                    plugins_root,
                    f"missing generated plugin '{name}'",
                )
        for name in generated_names:
            if name not in core_plugins:
                _add(
                    issues,
                    root,
                    plugins_root / name,
                    f"unexpected generated plugin '{name}'",
                )
    _validate_marketplace(root, core_plugins, issues)
    return sorted(issues, key=lambda issue: (issue.path.as_posix(), issue.message))
