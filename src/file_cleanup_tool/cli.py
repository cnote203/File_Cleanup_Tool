"""Command line: file-cleanup (or python -m file_cleanup_tool)."""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from typing import List, Optional

from . import __version__
from .apply import apply_plan
from .demo import make_demo
from .errors import CleanupError
from .explorer import build_page
from .plan import read_plan, write_plan
from .rules import load_rules, suggest
from .scanner import read_inventory, scan, write_inventory

DESCRIPTION = """File Cleanup Tool
Point it at a folder, review it visually with your team, then copy the approved layout into a new,
clean folder. Standard library only. Your original files are never changed.
"""


def cmd_demo(a) -> int:
    n = make_demo(a.path)
    print(f"Created {n} messy sample files in {a.path}")
    print(f"Next: file-cleanup explore {a.path}")
    return 0


def _scan_to(path: str, out: str, include_system: bool) -> list:
    res = scan(path, include_system)
    write_inventory(res.rows, out)
    print(f"{res.file_count:,} files and {res.folder_count:,} folders -> {out}")
    if res.errors:
        print(f"{len(res.errors)} items could not be read (first 5):")
        for e in res.errors[:5]:
            print("  ", e)
    return res.rows


def cmd_scan(a) -> int:
    _scan_to(a.path, a.out, a.include_system)
    return 0


def cmd_explore(a) -> int:
    os.makedirs(a.out_dir, exist_ok=True)
    inv = os.path.join(a.out_dir, "inventory.csv")
    _scan_to(a.path, inv, False)
    with open(inv, encoding="utf-8-sig") as f:
        text = f.read()
    plan = None
    if a.plan:
        try:
            with open(a.plan, encoding="utf-8-sig") as f:
                plan = f.read()
        except OSError as e:
            raise CleanupError(f"Could not read {a.plan}: {e}") from e
    page = build_page(text, os.path.join(a.out_dir, "explorer.html"), plan)
    print(f"Explorer page: {page}")
    print("It runs fully offline. Decisions are kept in your browser; use Export to save them.")
    if not a.no_open:
        webbrowser.open("file://" + os.path.abspath(page).replace("\\", "/"))
    return 0


def cmd_suggest(a) -> int:
    rs = load_rules(a.rules)
    inventory = read_inventory(a.inventory)
    rows = suggest(rs, inventory)
    write_plan(rows, a.out)
    counts = {}
    for r in rows:
        counts[r["action"]] = counts.get(r["action"], 0) + 1
    print(f"{len(rows):,} files -> {a.out}")
    print("  " + ", ".join(f"{v:,} {k.lower()}" for k, v in sorted(counts.items())))
    print(f"Review it with: file-cleanup explore PATH --plan {a.out}")
    return 0


def cmd_apply(a) -> int:
    plan = read_plan(a.plan, a.undecided)
    print(f"Plan: {a.plan}")
    print(plan.describe())
    report = apply_plan(
        a.src, a.dest, plan, go=a.go, log_path=a.log, allow_synced=a.allow_synced,
        progress=lambda i, n: print(f"  {i:,} / {n:,}"),
    )
    for w in report.warnings:
        print("Warning:", w)
    if report.renamed:
        print(f"{report.renamed:,} files share a destination name; the later ones get (2), (3)...")
    print(f"{len(report.todo):,} files to copy ({'COPYING' if a.go else 'DRY RUN'}); "
          f"{report.without_destination} rows without a destination skipped; {len(report.missing)} source files missing")
    for m in report.missing[:10]:
        print("  missing:", m)
    if not a.go:
        for it in report.todo[:15]:
            print(f"  [{it.action}] {it.old_path}\n      -> {it.new_path}")
        print("\nNothing was written. Add --go to copy.")
        return 0
    print(f"Copied {report.copied:,}, already done {report.skipped:,}, failed {report.failed:,}. Log: {report.log_path}")
    return 1 if report.failed else 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="file-cleanup", description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="command")

    p = sub.add_parser("demo", help="make a messy practice folder")
    p.add_argument("path", nargs="?", default="demo_folder")
    p.set_defaults(fn=cmd_demo)

    p = sub.add_parser("scan", help="write an inventory CSV of a folder")
    p.add_argument("path")
    p.add_argument("--out", default="inventory.csv")
    p.add_argument("--include-system", action="store_true", help="keep desktop.ini, Thumbs.db and .DS_Store")
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("explore", help="scan a folder and open the offline explorer page")
    p.add_argument("path")
    p.add_argument("--out-dir", default="cleanup-output")
    p.add_argument("--no-open", action="store_true", help="build the page but do not open a browser")
    p.add_argument("--plan", help="a plan or mapping CSV to show as the proposed structure")
    p.set_defaults(fn=cmd_explore)

    p = sub.add_parser("suggest", help="draft a plan from a rules file")
    p.add_argument("--inventory", default="inventory.csv", help="inventory CSV from 'scan' (default: inventory.csv)")
    p.add_argument("--rules", required=True, help="rules JSON file, see docs/rules.md")
    p.add_argument("--out", default="suggested_plan.csv")
    p.set_defaults(fn=cmd_suggest)

    p = sub.add_parser("apply", help="copy files into the new structure (dry run unless --go)")
    p.add_argument("--src", required=True, help="the original folder")
    p.add_argument("--dest", required=True, help="the new, empty folder")
    p.add_argument("--plan", required=True, help="cleanup_action_plan.csv from the explorer, or a mapping sheet")
    p.add_argument("--undecided", choices=["skip", "keep"], default="skip",
                   help="files with no decision: skip them (default) or copy them to the same relative path")
    p.add_argument("--log", default="copy_log.csv")
    p.add_argument("--allow-synced", action="store_true", help="allow a OneDrive/SharePoint destination")
    p.add_argument("--go", action="store_true", help="actually copy")
    p.set_defaults(fn=cmd_apply)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except CleanupError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped. Run the same command again to resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
