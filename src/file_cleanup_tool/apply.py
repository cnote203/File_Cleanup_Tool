"""Copy files into a new structure. Originals are never changed or deleted."""
from __future__ import annotations

import csv
import os
import shutil
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .errors import CleanupError
from .paths import is_inside, long_path, looks_synced, to_native
from .plan import Plan, PlanItem, unique_destinations


@dataclass
class ApplyReport:
    todo: List[PlanItem] = field(default_factory=list)
    without_destination: int = 0
    renamed: int = 0
    missing: List[str] = field(default_factory=list)
    copied: int = 0
    skipped: int = 0
    failed: int = 0
    log_path: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def check_destination(src: str, dest: str, allow_synced: bool = False) -> List[str]:
    """Raise if the destination is unsafe; return any warnings."""
    if not os.path.isdir(long_path(src)):
        raise CleanupError(f"Source folder not found: {src}")
    if is_inside(dest, src):
        raise CleanupError("The destination cannot be the source folder or inside it.")
    warnings = []
    if looks_synced(dest):
        if not allow_synced:
            raise CleanupError(
                "The destination looks like a OneDrive/SharePoint synced folder, so the copies would upload. "
                "Choose a folder outside it, or add --allow-synced if that is what you want."
            )
        warnings.append("The destination is a synced folder; copies will upload.")
    return warnings


def apply_plan(
    src: str,
    dest: str,
    plan: Plan,
    go: bool = False,
    log_path: str = "copy_log.csv",
    allow_synced: bool = False,
    progress: Optional[Callable[[int, int], None]] = None,
) -> ApplyReport:
    """Dry run by default. With go=True, copy each planned file and verify its size.

    Safe to stop and re-run: a file already at the destination with the same size is skipped.
    """
    report = ApplyReport(warnings=check_destination(src, dest, allow_synced))
    with_dest = [it for it in plan.items if it.new_path]
    report.without_destination = len(plan.items) - len(with_dest)
    report.todo, report.renamed = unique_destinations(with_dest)
    report.missing = [
        it.old_path for it in report.todo if not os.path.isfile(long_path(os.path.join(src, to_native(it.old_path))))
    ]
    if not go:
        return report

    report.log_path = log_path
    new_log = not os.path.exists(log_path)
    with open(log_path, "a", encoding="utf-8", newline="") as log:
        w = csv.writer(log)
        if new_log:
            w.writerow(["old_path", "new_path", "status", "detail"])
        for i, it in enumerate(report.todo, 1):
            s = long_path(os.path.join(src, to_native(it.old_path)))
            d = long_path(os.path.join(dest, to_native(it.new_path)))
            if os.path.isfile(d) and os.path.isfile(s) and os.path.getsize(d) == os.path.getsize(s):
                report.skipped += 1
                continue
            try:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
                if os.path.getsize(s) != os.path.getsize(d):
                    raise IOError("size mismatch after copy")
                w.writerow([it.old_path, it.new_path, "ok", ""])
                report.copied += 1
            except Exception as e:  # keep going; every failure is logged
                w.writerow([it.old_path, it.new_path, "failed", str(e)])
                report.failed += 1
            log.flush()
            if progress and i % 100 == 0:
                progress(i, len(report.todo))
    return report
