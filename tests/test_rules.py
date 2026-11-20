import datetime as dt
import json

from file_cleanup_tool import CleanupError, load_rules, parse_rules, suggest

from .helpers import TempCase

TODAY = dt.date(2026, 6, 1)


def row(path, modified="2026-01-15", size="10"):
    name = path.split("\\")[-1]
    ext = "." + name.rsplit(".", 1)[1].lower() if "." in name else ""
    return {"path": path, "name": name, "type": "file", "ext": ext, "size_kb": size, "modified": modified}


RULES = {
    "archive_root": "Old stuff",
    "rules": [
        {"name": "Invoices", "match": {"name_regex": "(?i)^inv", "ext": ["pdf"]}, "folder": "Finance/Invoices/{year}"},
        {"name": "Stale", "match": {"older_than_years": 2}, "action": "archive"},
        {"name": "Pics", "match": {"path_glob": "*/photos/*", "ext": [".jpg", ".png"]}, "folder": "Media/{parent}", "rename": "{modified} {name}"},
        {"name": "Keepers", "match": {"top_folder": "Policies"}, "action": "keep"},
    ],
}


class RuleTests(TempCase):
    def run_rules(self, rows, rules=RULES):
        return {r["old_path"]: r for r in suggest(parse_rules(rules), rows, TODAY)}

    def test_first_match_wins_and_templates(self):
        out = self.run_rules([row("Misc\\INV-001.PDF", "2025-03-02"), row("Misc\\old.txt", "2019-01-01")])
        inv = out["Misc\\INV-001.PDF"]
        self.assertEqual((inv["action"], inv["new_path"], inv["rule"]), ("Move", "Finance\\Invoices\\2025\\INV-001.PDF", "Invoices"))
        old = out["Misc\\old.txt"]
        self.assertEqual((old["action"], old["new_path"]), ("Archive", "Old stuff\\Misc\\old.txt"))

    def test_glob_rename_and_keep(self):
        out = self.run_rules([row("Trip\\photos\\a.jpg", "2026-02-02"), row("Policies\\hr.docx")])
        self.assertEqual(out["Trip\\photos\\a.jpg"]["new_path"], "Media\\photos\\2026-02-02 a.jpg")
        self.assertEqual((out["Policies\\hr.docx"]["action"], out["Policies\\hr.docx"]["new_path"]), ("Keep", "Policies\\hr.docx"))

    def test_unmatched_uses_default(self):
        out = self.run_rules([row("x\\y.txt")])
        self.assertEqual((out["x\\y.txt"]["action"], out["x\\y.txt"]["new_path"]), ("Undecided", ""))
        keep = dict(RULES, default_action="keep")
        out = self.run_rules([row("x\\y.txt")], keep)
        self.assertEqual(out["x\\y.txt"]["new_path"], "x\\y.txt")

    def test_size_and_age_conditions(self):
        rules = {"rules": [{"name": "Big", "match": {"min_size_kb": 1000}, "folder": "Big"},
                           {"name": "Fresh", "match": {"newer_than_days": 30}, "folder": "Fresh"}]}
        out = self.run_rules([row("a.bin", size="2048"), row("b.txt", modified="2026-05-20"), row("c.txt", modified="")], rules)
        self.assertEqual(out["a.bin"]["rule"], "Big")
        self.assertEqual(out["b.txt"]["rule"], "Fresh")
        self.assertEqual(out["c.txt"]["rule"], "")  # unknown date never matches an age rule

    def test_folders_in_the_inventory_are_ignored(self):
        rows = [dict(row("Dir"), type="folder"), row("Dir\\f.txt")]
        self.assertEqual(len(suggest(parse_rules(RULES), rows, TODAY)), 1)

    def test_validation_errors(self):
        bad = [
            {"rules": [{"name": "r", "match": {}, "folder": "x"}]},
            {"rules": [{"name": "r", "match": {"bogus": 1}, "folder": "x"}]},
            {"rules": [{"name": "r", "match": {"ext": ["pdf"]}}]},
            {"rules": [{"name": "r", "match": {"ext": ["pdf"]}, "folder": "{nope}"}]},
            {"rules": [{"name": "r", "match": {"name_regex": "("}, "folder": "x"}]},
            {"rules": [{"name": "r", "match": {"ext": ["pdf"]}, "action": "explode"}]},
            {"rules": [], "default_action": "maybe"},
            {"rules": [], "default_action": "archive"},
            {"nothing": True},
        ]
        for doc in bad:
            with self.assertRaises(CleanupError, msg=str(doc)):
                parse_rules(doc)

    def test_load_rules_errors(self):
        with self.assertRaises(CleanupError):
            load_rules("missing.json")
        with open("bad.json", "w") as f:
            f.write("{not json")
        with self.assertRaises(CleanupError) as cm:
            load_rules("bad.json")
        self.assertIn("not valid JSON", str(cm.exception))
        with open("ok.json", "w", encoding="utf-8-sig") as f:
            json.dump(RULES, f)
        self.assertEqual(len(load_rules("ok.json").rules), 4)
