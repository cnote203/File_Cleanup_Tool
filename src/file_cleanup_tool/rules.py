"""Turn a small rules file into a plan, so a first draft of the new structure needs no clicking.

A rules file is JSON:

    {
      "archive_root": "Archive",
      "default_action": "undecided",
      "rules": [
        {"name": "Invoices", "match": {"name_regex": "(?i)invoice|^inv-", "ext": [".pdf"]},
         "action": "move", "folder": "Finance/Invoices/{year}"},
        {"name": "Old files", "match": {"older_than_years": 3}, "action": "archive"}
      ]
    }

Rules are tried in order and the first one that matches a file wins. A rule matches when
every key in its "match" block is true. See docs/rules.md.
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import json
import re
import string
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .errors import CleanupError
from .paths import to_stored

MATCH_KEYS = {
    "path_glob", "path_regex", "name_regex", "ext", "min_size_kb", "max_size_kb",
    "older_than_days", "older_than_years", "newer_than_days", "top_folder",
}
ACTIONS = ("move", "archive", "keep", "undecided")
TEMPLATE_FIELDS = {"name", "stem", "ext", "parent", "top", "path", "year", "month", "modified"}


@dataclass
class Rule:
    name: str
    match: Dict
    action: str = "move"
    folder: str = ""
    rename: str = ""
    _path_re: Optional[re.Pattern] = field(default=None, repr=False)
    _name_re: Optional[re.Pattern] = field(default=None, repr=False)


@dataclass
class RuleSet:
    rules: List[Rule]
    archive_root: str = "Archive"
    default_action: str = "undecided"


def _check_template(text: str, where: str) -> None:
    try:
        names = {f for _, f, _, _ in string.Formatter().parse(text) if f}
    except ValueError as e:
        raise CleanupError(f"{where}: bad template {text!r} ({e})") from e
    bad = names - TEMPLATE_FIELDS
    if bad:
        raise CleanupError(f"{where}: unknown field {{{sorted(bad)[0]}}}. Allowed: {', '.join(sorted(TEMPLATE_FIELDS))}")


def _regex(pattern: str, where: str) -> re.Pattern:
    try:
        return re.compile(pattern)
    except re.error as e:
        raise CleanupError(f"{where}: invalid regular expression {pattern!r} ({e})") from e


def parse_rules(data: Dict) -> RuleSet:
    """Validate a rules document (already parsed from JSON) and return a RuleSet."""
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise CleanupError('Rules file must be an object with a "rules" list.')
    default = str(data.get("default_action", "undecided")).lower()
    if default not in ("undecided", "keep"):
        raise CleanupError("default_action must be 'undecided' or 'keep'")
    rs = RuleSet(rules=[], archive_root=to_stored(str(data.get("archive_root", "Archive"))).strip("\\") or "Archive",
                 default_action=default)
    for i, raw in enumerate(data["rules"], 1):
        name = str(raw.get("name") or f"rule {i}")
        where = f"rule '{name}'"
        match = raw.get("match") or {}
        if not isinstance(match, dict) or not match:
            raise CleanupError(f"{where}: needs a non-empty \"match\" block.")
        unknown = set(match) - MATCH_KEYS
        if unknown:
            raise CleanupError(f"{where}: unknown match key '{sorted(unknown)[0]}'. Allowed: {', '.join(sorted(MATCH_KEYS))}")
        action = str(raw.get("action", "move")).lower()
        if action not in ACTIONS:
            raise CleanupError(f"{where}: action must be one of {', '.join(ACTIONS)}")
        folder, rename = str(raw.get("folder", "")), str(raw.get("rename", ""))
        if action == "move" and not folder and not rename:
            raise CleanupError(f"{where}: a move rule needs a \"folder\" (and optionally a \"rename\").")
        _check_template(folder, where)
        _check_template(rename, where)
        rule = Rule(name=name, match=match, action=action, folder=folder, rename=rename)
        if "path_regex" in match:
            rule._path_re = _regex(match["path_regex"], where)
        if "name_regex" in match:
            rule._name_re = _regex(match["name_regex"], where)
        rs.rules.append(rule)
    return rs


def load_rules(path: str) -> RuleSet:
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except OSError as e:
        raise CleanupError(f"Could not read rules file {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise CleanupError(f"{path} is not valid JSON: line {e.lineno}, column {e.colno}: {e.msg}") from e
    return parse_rules(data)


def _age_days(modified: str, today: dt.date) -> Optional[int]:
    try:
        return (today - dt.date.fromisoformat(modified)).days
    except (TypeError, ValueError):
        return None


def _matches(rule: Rule, row: Dict, today: dt.date) -> bool:
    m = rule.match
    path = row["path"]
    posix = path.replace("\\", "/")
    parts = path.split("\\")
    if "top_folder" in m and not (len(parts) > 1 and parts[0].lower() == str(m["top_folder"]).lower()):
        return False
    if "path_glob" in m:
        pats = m["path_glob"] if isinstance(m["path_glob"], list) else [m["path_glob"]]
        if not any(fnmatch.fnmatchcase(posix.lower(), str(p).replace("\\", "/").lower()) for p in pats):
            return False
    if rule._path_re is not None and not rule._path_re.search(path):
        return False
    if rule._name_re is not None and not rule._name_re.search(row["name"]):
        return False
    if "ext" in m:
        exts = [e.lower() if e.startswith(".") else "." + e.lower() for e in (m["ext"] if isinstance(m["ext"], list) else [m["ext"]])]
        if row.get("ext", "").lower() not in exts:
            return False
    try:
        size = float(row.get("size_kb") or 0)
    except ValueError:
        size = 0.0
    if "min_size_kb" in m and size < float(m["min_size_kb"]):
        return False
    if "max_size_kb" in m and size > float(m["max_size_kb"]):
        return False
    age = _age_days(row.get("modified", ""), today)
    for key, days in (("older_than_days", 1), ("older_than_years", 365)):
        if key in m and (age is None or age < float(m[key]) * days):
            return False
    if "newer_than_days" in m and (age is None or age > float(m["newer_than_days"])):
        return False
    return True


def _context(row: Dict) -> Dict[str, str]:
    parts = row["path"].split("\\")
    stem, ext = row["name"].rsplit(".", 1) if "." in row["name"].lstrip(".") else (row["name"], "")
    mod = row.get("modified") or ""
    return {
        "name": row["name"], "stem": stem, "ext": ("." + ext) if ext else "",
        "parent": parts[-2] if len(parts) > 1 else "", "top": parts[0] if len(parts) > 1 else "",
        "path": row["path"], "year": mod[:4] or "unknown", "month": mod[5:7] or "unknown", "modified": mod or "unknown",
    }


def decide(rs: RuleSet, row: Dict, today: Optional[dt.date] = None) -> Dict:
    """Return the plan row for one inventory row."""
    today = today or dt.date.today()
    base = {"old_path": row["path"], "size_kb": row.get("size_kb", ""), "modified": row.get("modified", "")}
    for rule in rs.rules:
        if not _matches(rule, row, today):
            continue
        ctx = _context(row)
        name = rule.rename.format_map(ctx) if rule.rename else row["name"]
        folder = to_stored(rule.folder.format_map(ctx)).strip("\\")
        if rule.action == "move":
            new = (folder + "\\" if folder else "") + name
        elif rule.action == "archive":
            new = rs.archive_root + "\\" + ((folder + "\\" + name) if folder else row["path"])
        elif rule.action == "keep":
            new = row["path"]
        else:
            new = ""
        return {**base, "new_path": new, "action": rule.action.capitalize(), "rule": rule.name}
    keep = rs.default_action == "keep"
    return {**base, "new_path": row["path"] if keep else "", "action": rs.default_action.capitalize(), "rule": ""}


def suggest(rs: RuleSet, inventory: Iterable[Dict], today: Optional[dt.date] = None) -> List[Dict]:
    """Apply the rules to every file in an inventory and return plan rows."""
    return [decide(rs, r, today) for r in inventory if (r.get("type") or "file") == "file"]
