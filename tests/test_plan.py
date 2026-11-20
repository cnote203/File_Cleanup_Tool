from file_cleanup_tool import CleanupError, read_plan
from file_cleanup_tool.plan import PlanItem, unique_destinations

from .helpers import TempCase


class PlanTests(TempCase):
    def test_explorer_export_format(self):
        p = self.write_csv("plan.csv", ["path", "type", "size_kb", "action", "new_path"], [
            ["A\\one.txt", "file", 1, "move", "B\\one.txt"],
            ["A\\two.txt", "file", 1, "ARCHIVE", "Archive\\A\\two.txt"],
            ["A\\three.txt", "file", 1, "keep", ""],
            ["A\\four.txt", "file", 1, "delete", ""],
            ["A\\five.txt", "file", 1, "discuss", ""],
            ["A\\six.txt", "file", 1, "undecided", ""],
            ["A", "folder", "", "move", "X"],
        ], bom=True)
        plan = read_plan(p)
        self.assertEqual([(i.old_path, i.new_path, i.action) for i in plan.items], [
            ("A\\one.txt", "B\\one.txt", "move"),
            ("A\\two.txt", "Archive\\A\\two.txt", "archive"),
            ("A\\three.txt", "A\\three.txt", "keep"),
        ])
        self.assertEqual(plan.counts, {"move": 1, "archive": 1, "keep": 1, "delete": 1, "discuss": 1, "undecided": 1})
        self.assertIn("Left out", plan.describe())

    def test_mapping_sheet_format(self):
        p = self.write_csv("map.csv", ["old_path", "new_path", "action"], [
            ["a.txt", "01\\a.txt", "Move"],
            ["b.txt", "", "Duplicate - ignored"],
        ])
        plan = read_plan(p)
        self.assertEqual(len(plan.items), 1)
        self.assertEqual(plan.counts["duplicate"], 1)

    def test_undecided_keep(self):
        p = self.write_csv("p.csv", ["path", "type", "action", "new_path"], [["a.txt", "file", "", ""]])
        self.assertEqual(read_plan(p).items, [])
        self.assertEqual(read_plan(p, undecided="keep").items, [PlanItem("a.txt", "a.txt", "keep")])
        with self.assertRaises(CleanupError):
            read_plan(p, undecided="nope")

    def test_rejects_wrong_csv(self):
        p = self.write_csv("bad.csv", ["name", "size"], [["a", "1"]])
        with self.assertRaises(CleanupError) as cm:
            read_plan(p)
        self.assertIn("Columns found", str(cm.exception))

    def test_empty_and_missing(self):
        p = self.write_csv("empty.csv", ["path", "action"], [])
        with self.assertRaises(CleanupError):
            read_plan(p)
        with self.assertRaises(CleanupError):
            read_plan("nope.csv")

    def test_unique_destinations(self):
        items = [PlanItem("a", "X\\f.txt", "move"), PlanItem("b", "x\\F.txt", "move"),
                 PlanItem("c", "X\\f (2).txt", "move"), PlanItem("d", "X\\f.txt", "move")]
        out, renamed = unique_destinations(items)
        self.assertEqual([i.new_path for i in out], ["X\\f.txt", "x\\F (2).txt", "X\\f (2) (2).txt", "X\\f (3).txt"])
        self.assertEqual(len({i.new_path.lower() for i in out}), 4)  # no two files share a path
        self.assertEqual(renamed, 3)
