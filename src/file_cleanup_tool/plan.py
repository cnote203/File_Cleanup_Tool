"""Read and normalise action plans.

Two CSV layouts are accepted:

* the explorer's "Export action plan"  ->  path,type,action,new_path,...
* a mapping sheet                      ->  old_path,new_path,action

Column names are case-insensitive and a UTF-8 BOM is fine.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from .errors import CleanupError

COPY_ACTIONS = ("move", "archive", "keep")
PLAN_COLUMNS = ["old_path", "new_path", "action", "rule", "size_kb", "modified"]


@dataclass(frozen=True)
class PlanItem:
    old_path: str
    new_path: str
    action: str


@dataclass
class Plan:
    items: List[PlanItem] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)

    def describe(self) -> str:
        copied = {k: v for k, v in self.counts.items() if k in COPY_ACTIONS}
        left = {k: v for k, v in self.counts.items() if k not in COPY_ACTIONS}
        c = ", ".join(f"{v:,} {k}" for k, v in sorted(copied.items())) or "nothing"
        l = ", ".join(f"{v:,} {k}" for k, v in sorted(left.items())) or "nothing"
        return f"  Copied by action : {c}\n  Left out         : {l}"


def read_plan(path: str, undecided: str = "skip") -> Plan:
    """Read a plan file.

    undecided="skip" leaves files with no decision out; "keep" copies them to their
    current relative path so the result mirrors the explorer's "after my decisions" view.
    """
    if undecided not in ("skip", "keep"):
        raise CleanupError("undecided must be 'skip' or 'keep'")
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            raw = [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    except OSError as e:
        raise CleanupError(f"Could not read plan {path}: {e}") from e
    if not raw:
        raise CleanupError(f"{path} has no rows.")
    cols = raw[0].keys()
    if "action" not in cols or not ("path" in cols or "old_path" in cols):
        raise CleanupError(
            f"{path} is not an action plan or mapping sheet: it needs an 'action' column and a 'path' or "
            f"'old_path' column. Columns found: {', '.join(cols)}"
        )
    plan = Plan()
    for r in raw:
        old = r.get("path") or r.get("old_path") or ""
        if not old or (r.get("type") or "file").lower() == "folder":
            continue
        act = (r.get("action") or "").lower()
        if act.startswith("duplicate"):
            act = "duplicate"
        key = act or "undecided"
        plan.counts[key] = plan.counts.get(key, 0) + 1
        new = r.get("new_path") or ""
        if act in COPY_ACTIONS:
            plan.items.append(PlanItem(old, new or (old if act == "keep" else ""), act))
        elif key == "undecided" and undecided == "keep":
            plan.items.append(PlanItem(old, old, "keep"))
    return plan


def unique_destinations(items: Iterable[PlanItem]) -> Tuple[List[PlanItem], int]:
    """Give files that would land on the same path a (2), (3)... suffix. Returns (items, renamed)."""
    taken, out, renamed = set(), [], 0
    for it in items:
        new = it.new_path
        if not new:
            out.append(it)
            continue
        if new.lower() in taken:
            base, ext = os.path.splitext(new)
            n = 2
            while f"{base} ({n}){ext}".lower() in taken:
                n += 1
            new = f"{base} ({n}){ext}"
            renamed += 1
        taken.add(new.lower())
        out.append(PlanItem(it.old_path, new, it.action))
    return out, renamed


def write_plan(rows: Iterable[Dict], path: str) -> None:
    """Write a mapping sheet (used by the rules engine)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PLAN_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
