from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Platform-specific patterns to neutralize in portable core SKILL.md bodies.
_NEUTRALIZE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bTask tool\b", re.I),
        "parallel worker tool (see references/platform-orchestration.md)",
    ),
    (
        re.compile(r"\bsubagent_type:\s*\w+", re.I),
        "platform-specific subagent (see references/platform-orchestration.md)",
    ),
    (
        re.compile(r"\bvia Task tool\b", re.I),
        "via parallel workers",
    ),
    (
        re.compile(r"Part of (the )?\w+ plugin\.?", re.I),
        "",
    ),
    (
        re.compile(r"Loads? .+ from (the )?\w+ plugin\.?", re.I),
        "Load the named skill and follow its SKILL.md.",
    ),
    (
        re.compile(r"model:\s*fast\s*\n", re.I),
        "",
    ),
]

_CURSOR_PATH_PRIORITY = [
    (r"\.cursor/CODING_REQUIREMENTS\.md", "docs/CODING_REQUIREMENTS.md (see platform-paths.md)"),
    (r"\.cursor/instructions\.md", "platform instructions file (see platform-paths.md)"),
    (r"@\.cursor/instructions\.md", "@platform instructions (see platform-paths.md)"),
]


def detect_platform(skill_dir: Path) -> str:
    """Guess source platform from skill content or parent path."""
    path_str = str(skill_dir).lower()
    if "incoming/cursor" in path_str or ".cursor-plugin" in path_str:
        return "cursor"
    if "incoming/claude" in path_str or "/.claude/" in path_str:
        return "claude"
    if "incoming/codex" in path_str or "/.agents/" in path_str:
        return "codex"
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8").lower()
        if "task tool" in text or "subagent_type" in text:
            return "cursor"
        if "allowed-tools:" in text and "claude" in text:
            return "claude"
    return "portable"


def read_frontmatter(skill_md: Path) -> tuple[dict[str, Any], str, str]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not match:
        return {}, text, ""
    body = text[match.end() :]
    meta = yaml.safe_load(match.group(1)) or {}
    return meta, body, text


def write_skill_md(skill_dir: Path, meta: dict[str, Any], body: str) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    front = yaml.safe_dump(meta, default_flow_style=False, sort_keys=False).strip()
    content = f"---\n{front}\n---\n\n{body.lstrip()}"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def normalize_skill_body(body: str, *, source_platform: str) -> str:
    result = body
    for pattern, replacement in _NEUTRALIZE_PATTERNS:
        result = pattern.sub(replacement, result)
    for pattern, replacement in _CURSOR_PATH_PRIORITY:
        result = re.sub(pattern, replacement, result)
    # collapse extra blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip() + "\n"


def normalize_skill_dir(
    skill_dir: Path,
    skill_name: str | None = None,
    *,
    source_platform: str | None = None,
) -> str:
    """Normalize a skill directory for portable core. Returns canonical skill name."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise ValueError(f"Missing SKILL.md in {skill_dir}")

    name = skill_name or skill_dir.name
    if not NAME_RE.match(name):
        raise ValueError(f"Invalid skill directory name: {name}")

    platform = source_platform or detect_platform(skill_dir)
    meta, body, _ = read_frontmatter(skill_md)

    meta["name"] = name
    if not meta.get("description"):
        raise ValueError(f"Skill '{name}' missing description in frontmatter")
    meta.setdefault("license", "MIT")
    if "metadata" not in meta or not isinstance(meta.get("metadata"), dict):
        meta["metadata"] = {}
    meta["metadata"].setdefault("source_platform", platform)
    meta["metadata"].setdefault("ingested_by", "skills-export")

    # Strip experimental Cursor-only frontmatter
    meta.pop("model", None)

    body = normalize_skill_body(body, source_platform=platform)
    write_skill_md(skill_dir, meta, body)
    return name


def validate_skill_dir(skill_dir: Path, skill_name: str | None = None) -> list[str]:
    errors: list[str] = []
    name = skill_name or skill_dir.name
    if not NAME_RE.match(name):
        errors.append(f"{name}: invalid directory name")
    if not (skill_dir / "SKILL.md").is_file():
        errors.append(f"{name}: missing SKILL.md")
        return errors
    meta, _, _ = read_frontmatter(skill_dir / "SKILL.md")
    if meta.get("name") and meta["name"] != name:
        errors.append(f"{name}: frontmatter name '{meta['name']}' != directory")
    if not meta.get("description"):
        errors.append(f"{name}: missing description")
    return errors
