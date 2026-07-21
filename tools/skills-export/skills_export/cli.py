from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .assemble import PLATFORMS, export_all, export_flat_skills, export_platform
from .ingest import ingest_landing, write_ingest_report
from .manifest import load_manifest, platform_plugin_names, repo_root
from .validate import validate_core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skills-export",
        description="Ingest landing/skills into core; assemble Cursor/Claude/Codex plugins into dist/.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--root", type=Path, default=None)

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="Validate core skills + manifest")

    p_export = sub.add_parser("export", help="Assemble plugins into dist/")
    p_export.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=[*PLATFORMS, "all"],
    )
    p_export.add_argument("--plugin", action="append", dest="plugins")
    p_export.add_argument("-o", "--output", type=Path, default=None)
    p_export.add_argument(
        "--flat",
        action="store_true",
        help="Also write flat skills/ (claude/codex)",
    )

    p_list = sub.add_parser("list", help="List plugins and skills")
    p_list.add_argument("--plugins", action="store_true")
    p_list.add_argument("--skills", action="store_true")

    p_ingest = sub.add_parser("ingest", help="landing/skills → core")
    p_ingest.add_argument("--dry-run", action="store_true")

    p_maintain = sub.add_parser("maintain", help="ingest → validate → export all")
    p_maintain.add_argument("--dry-run", action="store_true")
    p_maintain.add_argument("--skip-ingest", action="store_true")
    p_maintain.add_argument("--skip-export", action="store_true")
    p_maintain.add_argument("--plugin", action="append", dest="plugins")

    # Aliases kept for muscle memory
    sub.add_parser("sync", help="Alias for export all").add_argument(
        "target", nargs="?", default="all", choices=[*PLATFORMS, "all"]
    )
    sub.add_parser("translate", help="Alias for maintain")

    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()

    if args.command == "validate":
        errors = validate_core(root)
        if errors:
            print("Validation failed:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        manifest = load_manifest(root)
        n_plugins = len(manifest["plugins"])
        n_skills = len({s for p in manifest["plugins"].values() for s in p["skills"]})
        print(f"OK: {n_plugins} plugins, {n_skills} core skills")
        return 0

    if args.command == "list":
        manifest = load_manifest(root)
        show_all = not args.plugins and not args.skills
        if show_all or args.plugins:
            print("Plugins:")
            for name, meta in manifest["plugins"].items():
                print(f"  {name}: {', '.join(meta['skills'])}")
        if show_all or args.skills:
            print("Core skills:")
            seen: set[str] = set()
            for meta in manifest["plugins"].values():
                for skill in meta["skills"]:
                    if skill not in seen:
                        seen.add(skill)
                        print(f"  {skill}")
        return 0

    if args.command in ("export", "sync"):
        target = getattr(args, "target", "all")
        plugins = getattr(args, "plugins", None)
        targets = list(PLATFORMS) if target == "all" else [target]
        for platform in targets:
            out = args.output if getattr(args, "output", None) and target != "all" else root / "dist" / platform
            if getattr(args, "output", None) and target == "all":
                out = args.output / platform
            paths = export_platform(root, platform, out, plugins=plugins)
            if getattr(args, "flat", False) and platform in {"claude", "codex"}:
                export_flat_skills(root, out, platform=platform, plugins=plugins)
            print(f"exported {platform} -> {out} ({len(paths)} plugins)")
        return 0

    if args.command == "ingest":
        result = ingest_landing(root, dry_run=args.dry_run)
        write_ingest_report(root, result)
        if result.ingested_skills:
            print(f"ingested: {', '.join(result.ingested_skills)}")
        if result.errors:
            for err in result.errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("ingest OK" + (" (dry-run)" if args.dry_run else ""))
        return 0

    if args.command in ("maintain", "translate"):
        dry_run = getattr(args, "dry_run", False)
        if not getattr(args, "skip_ingest", False):
            result = ingest_landing(root, dry_run=dry_run)
            write_ingest_report(root, result)
            if result.errors:
                for err in result.errors:
                    print(f"  - {err}", file=sys.stderr)
                return 1
            if result.ingested_skills:
                print(f"ingested: {', '.join(result.ingested_skills)}")

        errors = validate_core(root)
        if errors:
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1

        if not getattr(args, "skip_export", False):
            if dry_run:
                manifest = load_manifest(root)
                for platform in PLATFORMS:
                    n = len(platform_plugin_names(manifest, platform))
                    print(f"would export {platform} ({n} plugins)")
            else:
                export_all(root, plugins=getattr(args, "plugins", None))
                for platform in PLATFORMS:
                    print(f"exported {platform} -> dist/{platform}/")
        print("maintain OK" + (" (dry-run)" if dry_run else ""))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
