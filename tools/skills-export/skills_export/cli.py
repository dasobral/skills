from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .exporters.claude import export_claude
from .exporters.codex import export_codex
from .exporters.cursor import export_cursor
from .ingest import ingest_landing, write_ingest_report
from .maintain import maintain
from .manifest import load_manifest, repo_root
from .validate import validate_core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skills-export",
        description=(
            "Unified skills framework: ingest landing zone, export to "
            "Cursor, Claude Code, and Codex."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect from cwd)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="Validate core skills against manifest")

    p_sync = sub.add_parser(
        "sync",
        help="Regenerate root-level Cursor plugins from core + adapters",
    )
    p_sync.add_argument(
        "target",
        choices=["cursor"],
        help="Sync target (currently cursor only)",
    )
    p_sync.add_argument(
        "--plugin",
        action="append",
        dest="plugins",
        help="Limit to specific plugin(s)",
    )

    p_export = sub.add_parser("export", help="Export bundles to dist/")
    p_export.add_argument(
        "target",
        choices=["cursor", "claude", "codex", "all"],
        help="Export target platform",
    )
    p_export.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: dist/<target>)",
    )
    p_export.add_argument(
        "--plugin",
        action="append",
        dest="plugins",
        help="Limit to specific plugin(s)",
    )
    p_export.add_argument(
        "--no-flat",
        action="store_true",
        help="Skip flat skill export (claude/codex only)",
    )
    p_export.add_argument(
        "--no-bundles",
        action="store_true",
        help="Skip per-plugin bundles (claude/codex only)",
    )

    p_list = sub.add_parser("list", help="List plugins and skills")
    p_list.add_argument("--plugins", action="store_true", help="List plugins only")
    p_list.add_argument("--skills", action="store_true", help="List skills only")

    p_ingest = sub.add_parser(
        "ingest",
        help="Ingest skills from landing/ into core (normalize + manifest)",
    )
    p_ingest.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate landing without writing core or archiving",
    )

    p_maintain = sub.add_parser(
        "maintain",
        help="Ingest landing → validate → sync Cursor → export Claude/Codex",
    )
    p_maintain.add_argument("--dry-run", action="store_true")
    p_maintain.add_argument("--skip-ingest", action="store_true")
    p_maintain.add_argument("--skip-export", action="store_true")
    p_maintain.add_argument("--plugin", action="append", dest="plugins")

    p_translate = sub.add_parser(
        "translate",
        help="Alias: maintain (ingest + export all platforms)",
    )
    p_translate.add_argument("--dry-run", action="store_true")
    p_translate.add_argument("--plugin", action="append", dest="plugins")

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
                skills = ", ".join(meta["skills"])
                print(f"  {name}: {skills}")
        if show_all or args.skills:
            print("Core skills:")
            seen: set[str] = set()
            for meta in manifest["plugins"].values():
                for skill in meta["skills"]:
                    if skill not in seen:
                        seen.add(skill)
                        print(f"  {skill}")
        return 0

    if args.command == "sync":
        if args.target == "cursor":
            paths = export_cursor(root, root, plugins=args.plugins, sync_root=True)
            for p in paths:
                print(f"synced {p.relative_to(root)}")
            print(f"Synced {len(paths)} Cursor plugin(s) to repo root")
        return 0

    if args.command == "export":
        targets = (
            ["cursor", "claude", "codex"] if args.target == "all" else [args.target]
        )
        for target in targets:
            out = args.output
            if out is None:
                out = root / "dist" / target
            else:
                out = out / target if args.target == "all" else out

            if target == "cursor":
                paths = export_cursor(root, out, plugins=args.plugins, sync_root=False)
            elif target == "claude":
                paths = export_claude(
                    root,
                    out,
                    plugins=args.plugins,
                    flat=not args.no_flat,
                    bundles=not args.no_bundles,
                )
            else:
                paths = export_codex(
                    root,
                    out,
                    plugins=args.plugins,
                    flat=not args.no_flat,
                    bundles=not args.no_bundles,
                )
            print(f"exported {target} -> {out} ({len(paths)} artifact(s))")
        return 0

    if args.command == "ingest":
        result = ingest_landing(root, dry_run=args.dry_run)
        write_ingest_report(root, result)
        if result.ingested_skills:
            print(f"ingested skills: {', '.join(result.ingested_skills)}")
        if result.ingested_plugins:
            print(f"ingested plugins: {', '.join(result.ingested_plugins)}")
        if result.archived:
            print(f"archived: {', '.join(result.archived)}")
        if result.errors:
            print("errors:", file=sys.stderr)
            for err in result.errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("ingest OK" + (" (dry-run)" if args.dry_run else ""))
        return 0

    if args.command in ("maintain", "translate"):
        result = maintain(
            root,
            dry_run=args.dry_run,
            skip_ingest=getattr(args, "skip_ingest", False),
            skip_export=False,
            plugins=getattr(args, "plugins", None),
        )
        if result.ingest_skills:
            print(f"ingested: {', '.join(result.ingest_skills)}")
        for platform, path in result.exports.items():
            print(f"exported {platform} -> {path}")
        errors = result.ingest_errors + result.validate_errors
        if errors:
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("maintain OK" + (" (dry-run)" if args.dry_run else ""))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
