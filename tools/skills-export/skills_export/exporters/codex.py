from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..manifest import copy_skill, load_manifest, plugin_skill_names, repo_root


def _bundle_readme(plugin_name: str, display_name: str, skills: list[str]) -> str:
    skill_list = "\n".join(f"- `{s}`" for s in skills)
    return f"""# {display_name} (Codex bundle)

Exported from portable core. Install skills into your project:

```bash
cp -r skills/* /path/to/project/.agents/skills/
```

Optional: reference instructions from `AGENTS.md`:

```
@.agents/instructions.md
```

## Skills

{skill_list}
"""


def export_codex_bundle(
    root: Path,
    plugin_name: str,
    output_dir: Path,
    *,
    clean: bool = True,
) -> Path:
    manifest = load_manifest(root)
    plugin_meta = manifest["plugins"][plugin_name]
    bundle_out = output_dir / "bundles" / plugin_name
    if clean and bundle_out.exists():
        shutil.rmtree(bundle_out)

    skills_out = bundle_out / ".agents" / "skills"
    skills_out.mkdir(parents=True, exist_ok=True)

    skill_names = plugin_skill_names(manifest, plugin_name)
    for skill in skill_names:
        copy_skill(root, skill, skills_out / skill)

    instructions = bundle_out / ".agents" / "instructions.md"
    instructions.write_text(
        """# Agent Instructions

Before writing or modifying code, read project conventions when present:
`docs/CODING_REQUIREMENTS.md`, `.agents/CODING_REQUIREMENTS.md`, or root `CODING_REQUIREMENTS.md`.

These requirements are authoritative.
""",
        encoding="utf-8",
    )

    agents_md = bundle_out / "AGENTS.md"
    agents_md.write_text("@.agents/instructions.md\n", encoding="utf-8")

    (bundle_out / "README.md").write_text(
        _bundle_readme(plugin_name, plugin_meta["display_name"], skill_names),
        encoding="utf-8",
    )

    meta = {
        "plugin": plugin_name,
        "display_name": plugin_meta["display_name"],
        "version": plugin_meta["version"],
        "skills": skill_names,
        "install": {
            "project_skills": ".agents/skills/",
            "user_skills": "~/.codex/skills/",
            "user_skills_alt": "~/.agents/skills/",
        },
    }
    (bundle_out / "bundle.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return bundle_out


def export_codex_flat(root: Path, output_dir: Path, *, clean: bool = True) -> Path:
    manifest = load_manifest(root)
    flat = output_dir / "skills"
    if clean and flat.exists():
        shutil.rmtree(flat)
    flat.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    for plugin in manifest["plugins"].values():
        for skill in plugin["skills"]:
            if skill in seen:
                continue
            seen.add(skill)
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
    plugins: list[str] | None = None,
    flat: bool = True,
    bundles: bool = True,
) -> list[Path]:
    root = root or repo_root()
    output_dir = output_dir or root / "dist" / "codex"
    manifest = load_manifest(root)
    results: list[Path] = []

    if bundles:
        names = plugins or list(manifest["plugins"].keys())
        for name in names:
            results.append(export_codex_bundle(root, name, output_dir))

    if flat:
        results.append(export_codex_flat(root, output_dir))

    refs_out = output_dir / "references"
    refs_src = root / "core" / "references"
    if refs_src.is_dir():
        if refs_out.exists():
            shutil.rmtree(refs_out)
        shutil.copytree(refs_src, refs_out)

    return results
