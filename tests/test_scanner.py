import os

from file_cleanup_tool import CleanupError, read_inventory, scan, write_inventory
from file_cleanup_tool.demo import DEMO, make_demo

from .helpers import TempCase


class ScannerTests(TempCase):
    def test_demo_scan_counts(self):
        self.assertEqual(make_demo("demo"), len(DEMO))
        res = scan("demo")
        self.assertEqual(res.file_count, len(DEMO))
        self.assertGreater(res.folder_count, 5)
        self.assertEqual(res.errors, [])

    def test_paths_use_backslashes_and_depth(self):
        self.make_files({"a/b/c.txt": "x"})
        rows = {r["path"]: r for r in scan(".").rows}
        self.assertIn("a\\b\\c.txt", rows)
        self.assertEqual(rows["a\\b\\c.txt"]["depth"], 3)
        self.assertEqual(rows["a\\b\\c.txt"]["ext"], ".txt")
        self.assertEqual(rows["a"]["type"], "folder")

    def test_system_files_skipped_unless_requested(self):
        self.make_files({"keep.txt": "x", "Thumbs.db": "x", "sub/desktop.ini": "x"})
        self.assertEqual([r["name"] for r in scan(".").rows if r["type"] == "file"], ["keep.txt"])
        names = {r["name"] for r in scan(".", include_system=True).rows}
        self.assertTrue({"Thumbs.db", "desktop.ini"} <= names)

    def test_missing_folder(self):
        with self.assertRaises(CleanupError):
            scan("does-not-exist")

    def test_inventory_round_trip(self):
        self.make_files({"x/y.pdf": "12345"})
        res = scan(".")
        write_inventory(res.rows, "inv.csv")
        back = read_inventory("inv.csv")
        self.assertEqual([r["path"] for r in back], [r["path"] for r in res.rows])
        with open("inv.csv", "rb") as f:
            self.assertTrue(f.read(3) == b"\xef\xbb\xbf")  # BOM so Excel opens it correctly

    def test_read_inventory_rejects_other_csv(self):
        p = self.write_csv("other.csv", ["a", "b"], [["1", "2"]])
        with self.assertRaises(CleanupError):
            read_inventory(p)
