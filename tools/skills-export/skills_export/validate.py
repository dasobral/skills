from __future__ import annotations

import re
from pathlib import Path

from .manifest import core_skills_dir, load_manifest, read_skill_frontmatter, repo_root

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_core(root: Path | None = None) -> list[str]:
    """Return list of validation errors (empty = ok)."""
    root = root or repo_root()
    manifest = load_manifest(root)
    errors: list[str] = []
    skills_root = core_skills_dir(root)

    declared = set()
    for plugin_name, plugin in manifest["plugins"].items():
        for skill in plugin["skills"]:
            declared.add(skill)
            skill_dir = skills_root / skill
            if not skill_dir.is_dir():
                errors.append(f"plugin '{plugin_name}': missing core skill '{skill}'")
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                errors.append(f"skill '{skill}': missing SKILL.md")
                continue
            meta = read_skill_frontmatter(skill_dir)
            name = meta.get("name", "")
            if not name:
                errors.append(f"skill '{skill}': SKILL.md missing 'name' in frontmatter")
            elif name != skill:
                errors.append(
                    f"skill '{skill}': frontmatter name '{name}' must match directory"
                )
            elif not NAME_RE.match(name):
                errors.append(f"skill '{skill}': invalid name format")
            desc = meta.get("description", "")
            if not desc or not str(desc).strip():
                errors.append(f"skill '{skill}': missing description")

    for skill_dir in skills_root.iterdir():
        if skill_dir.is_dir() and skill_dir.name not in declared:
            errors.append(f"orphan core skill '{skill_dir.name}' not listed in manifest")

    return errors
