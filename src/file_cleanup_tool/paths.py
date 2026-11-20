"""Path helpers shared by the other modules."""
from __future__ import annotations

import os

SYNCED_MARKERS = ("onedrive", "sharepoint")


def long_path(p: str) -> str:
    """Return the long-path form on Windows so paths over 260 characters work."""
    p = os.path.abspath(p)
    if os.name == "nt" and not p.startswith("\\\\?\\"):
        p = "\\\\?\\UNC\\" + p[2:] if p.startswith("\\\\") else "\\\\?\\" + p
    return p


def to_native(rel: str) -> str:
    """Convert a stored relative path (either slash style) to this OS's separator."""
    return rel.replace("\\", os.sep).replace("/", os.sep)


def to_stored(rel: str) -> str:
    """Stored paths always use backslashes, so inventories and plans are portable."""
    return rel.replace("/", "\\")


def is_inside(child: str, parent: str) -> bool:
    """True when child is the same folder as parent or sits below it."""
    c = os.path.normcase(os.path.abspath(child))
    p = os.path.normcase(os.path.abspath(parent))
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def looks_synced(path: str) -> bool:
    """True when the path looks like a OneDrive or SharePoint synced folder."""
    low = os.path.abspath(path).lower()
    return any(m in low for m in SYNCED_MARKERS)
