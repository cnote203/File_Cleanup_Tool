"""Walk a folder and describe everything in it. Read-only."""
from __future__ import annotations

import csv
import datetime as dt
import os
from dataclasses import dataclass, field
from typing import Dict, List

from .errors import CleanupError
from .paths import long_path

COLUMNS = ["path", "name", "type", "ext", "depth", "size_kb", "modified", "path_len"]
SYSTEM_FILES = {"desktop.ini", "thumbs.db", ".ds_store"}


@dataclass
class ScanResult:
    rows: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return sum(1 for r in self.rows if r["type"] == "file")

    @property
    def folder_count(self) -> int:
        return len(self.rows) - self.file_count


def scan(root: str, include_system: bool = False) -> ScanResult:
    """List every file and folder under root. Symlinks are skipped, nothing is modified."""
    root = os.path.abspath(root)
    if not os.path.isdir(long_path(root)):
        raise CleanupError(f"Folder not found: {root}")
    result = ScanResult()

    for cur, dirs, files in os.walk(long_path(root), onerror=lambda e: result.errors.append(str(e)), followlinks=False):
        cur_clean = cur[4:] if cur.startswith("\\\\?\\") else cur
        rel_dir = os.path.relpath(cur_clean, root)
        rel_dir = "" if rel_dir == "." else rel_dir
        dirs.sort(key=str.lower)
        for kind, names in (("folder", dirs), ("file", sorted(files, key=str.lower))):
            for n in names:
                if kind == "file" and not include_system and n.lower() in SYSTEM_FILES:
                    continue
                full = os.path.join(cur, n)
                if os.path.islink(full):
                    continue
                rel = ((rel_dir + os.sep + n) if rel_dir else n).replace(os.sep, "\\")
                try:
                    st = os.stat(full)
                except OSError as e:
                    result.errors.append(f"{rel}: {e}")
                    continue
                result.rows.append({
                    "path": rel,
                    "name": n,
                    "type": kind,
                    "ext": os.path.splitext(n)[1].lower() if kind == "file" else "",
                    "depth": rel.count("\\") + 1,
                    "size_kb": round(st.st_size / 1024, 1) if kind == "file" else "",
                    "modified": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
                    "path_len": len(rel),
                })
    return result


def write_inventory(rows, path: str) -> None:
    """Write scan rows to a CSV that Excel opens correctly (UTF-8 with BOM)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def read_inventory(path: str) -> List[Dict]:
    """Read an inventory CSV written by write_inventory."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        raise CleanupError(f"Could not read {path}: {e}") from e
    if rows and "path" not in rows[0]:
        raise CleanupError(f"{path} is not an inventory file (no 'path' column).")
    return rows
