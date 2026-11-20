"""Build the offline explorer page: a single HTML file with the inventory embedded."""
from __future__ import annotations

import json
import os
from importlib import resources
from typing import Optional

from .errors import CleanupError

DATA_MARK = "/*__DATA__*/"
MAP_MARK = "/*__MAP_MODULE__*/"


def _asset(name: str) -> str:
    try:
        return (resources.files("file_cleanup_tool") / "explorer" / name).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError) as e:
        raise CleanupError(
            f"The explorer file explorer/{name} is missing from the installed package. "
            "Reinstall the package, or see the Development section of the README."
        ) from e


def explorer_available() -> bool:
    try:
        _asset("template.html")
        _asset("map.js")
        return True
    except CleanupError:
        return False


def build_page(inventory_csv: str, out_html: str, plan_csv: Optional[str] = None) -> str:
    """Write the explorer page and return its path.

    inventory_csv and plan_csv are the CSV *text*, not paths. Everything stays inside the one
    HTML file; nothing is uploaded anywhere.
    """
    tpl, mapjs = _asset("template.html"), _asset("map.js")
    if DATA_MARK not in tpl or MAP_MARK not in tpl:
        raise CleanupError("explorer/template.html is missing a placeholder.")
    data = "window.__INVENTORY_CSV__ = " + json.dumps(inventory_csv).replace("</", "<\\/") + ";"
    if plan_csv:
        data += "\nwindow.__PLAN_CSV__ = " + json.dumps(plan_csv).replace("</", "<\\/") + ";"
    os.makedirs(os.path.dirname(os.path.abspath(out_html)), exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(tpl.replace(DATA_MARK, data).replace(MAP_MARK, mapjs))
    return out_html
