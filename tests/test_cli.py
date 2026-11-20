import contextlib
import csv
import io
import json
import os

from file_cleanup_tool.cli import main
from file_cleanup_tool.explorer import explorer_available

from .helpers import TempCase, read_text


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTests(TempCase):
    def test_full_flow_scan_suggest_apply(self):
        self.assertEqual(run("demo", "src")[0], 0)
        code, out, _ = run("scan", "src", "--out", "inv.csv")
        self.assertEqual(code, 0)
        self.assertIn("37 files", out)
        with open("rules.json", "w") as f:
            json.dump({"rules": [
                {"name": "Invoices", "match": {"path_glob": "finance/invoices/*"}, "folder": "Finance/Invoices"},
                {"name": "Old", "match": {"top_folder": "Archive"}, "action": "archive"},
            ]}, f)
        code, out, _ = run("suggest", "--inventory", "inv.csv", "--rules", "rules.json", "--out", "plan.csv")
        self.assertEqual(code, 0, out)
        rows = list(csv.DictReader(read_text("plan.csv", encoding="utf-8-sig").splitlines()))
        self.assertEqual(len(rows), 37)
        code, out, _ = run("apply", "--src", "src", "--dest", "new", "--plan", "plan.csv")
        self.assertIn("DRY RUN", out)
        self.assertFalse(os.path.exists("new"))
        code, out, _ = run("apply", "--src", "src", "--dest", "new", "--plan", "plan.csv", "--go")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(os.path.join("new", "Finance", "Invoices", "inv-001.pdf")))
        self.assertTrue(os.path.isfile(os.path.join("new", "Archive", "Archive", "old plan.docx")))

    def test_errors_exit_with_one_and_a_message(self):
        code, _, err = run("scan", "nope")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("error: Folder not found"))
        code, _, err = run("apply", "--src", ".", "--dest", "sub", "--plan", "x.csv")
        self.assertEqual(code, 1)

    def test_failed_copies_give_nonzero_exit(self):
        self.make_files({"src/a.txt": "a"})
        self.write_csv("p.csv", ["old_path", "new_path", "action"], [["gone.txt", "gone.txt", "Move"]])
        code, out, _ = run("apply", "--src", "src", "--dest", "out", "--plan", "p.csv", "--go")
        self.assertEqual(code, 1)
        self.assertIn("failed 1", out)

    def test_version_and_help(self):
        with self.assertRaises(SystemExit) as cm:
            run("--version")
        self.assertEqual(cm.exception.code, 0)

    def test_explore_builds_a_page_when_assets_exist(self):
        run("demo", "src")
        code, out, err = run("explore", "src", "--no-open", "--out-dir", "out")
        if explorer_available():
            self.assertEqual(code, 0, err)
            html = read_text(os.path.join("out", "explorer.html"), encoding="utf-8")
            self.assertIn("__INVENTORY_CSV__", html)
            self.assertNotIn("/*__DATA__*/", html)
        else:
            self.assertEqual(code, 1)
            self.assertIn("explorer", err)
