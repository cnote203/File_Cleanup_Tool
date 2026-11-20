import os

from file_cleanup_tool import CleanupError, apply_plan
from file_cleanup_tool.plan import Plan, PlanItem

from .helpers import TempCase, read_text


def plan_of(*items):
    return Plan(items=[PlanItem(*i) for i in items])


class ApplyTests(TempCase):
    def setUp(self):
        super().setUp()
        self.make_files({"src/a.txt": "aaa", "src/sub/b.txt": "bbbb", "src/sub/c.txt": "cc"})

    def test_dry_run_writes_nothing(self):
        r = apply_plan("src", "out", plan_of(("a.txt", "New\\a.txt", "move")))
        self.assertEqual(len(r.todo), 1)
        self.assertFalse(os.path.exists("out"))
        self.assertFalse(os.path.exists("copy_log.csv"))

    def test_copy_and_log(self):
        r = apply_plan("src", "out", plan_of(("a.txt", "New\\a.txt", "move"), ("sub\\b.txt", "Archive\\sub\\b.txt", "archive")), go=True)
        self.assertEqual((r.copied, r.failed, r.skipped), (2, 0, 0))
        self.assertEqual(read_text(os.path.join("out", "New", "a.txt")), "aaa")
        self.assertTrue(os.path.isfile(os.path.join("out", "Archive", "sub", "b.txt")))
        self.assertTrue(os.path.isfile("src/a.txt"))  # original untouched
        self.assertIn("ok", read_text("copy_log.csv"))

    def test_rerun_skips_finished_files(self):
        plan = plan_of(("a.txt", "a.txt", "keep"))
        apply_plan("src", "out", plan, go=True)
        r = apply_plan("src", "out", plan, go=True)
        self.assertEqual((r.copied, r.skipped), (0, 1))

    def test_new_destination_is_not_skipped(self):
        plan = plan_of(("a.txt", "a.txt", "keep"))
        apply_plan("src", "out1", plan, go=True)
        r = apply_plan("src", "out2", plan, go=True)  # same log file, different folder
        self.assertEqual(r.copied, 1)

    def test_name_collisions_get_a_suffix(self):
        r = apply_plan("src", "out", plan_of(("a.txt", "X\\f.txt", "move"), ("sub\\b.txt", "X\\f.txt", "move")), go=True)
        self.assertEqual(r.copied, 2)
        self.assertTrue(os.path.isfile(os.path.join("out", "X", "f (2).txt")))
        self.assertEqual(r.renamed, 1)

    def test_missing_source_is_reported_and_logged_as_failed(self):
        r = apply_plan("src", "out", plan_of(("gone.txt", "gone.txt", "keep")))
        self.assertEqual(r.missing, ["gone.txt"])
        r = apply_plan("src", "out", plan_of(("gone.txt", "gone.txt", "keep")), go=True)
        self.assertEqual(r.failed, 1)
        self.assertIn("failed", read_text("copy_log.csv"))

    def test_rows_without_destination_are_counted(self):
        r = apply_plan("src", "out", plan_of(("a.txt", "", "move")))
        self.assertEqual((r.without_destination, len(r.todo)), (1, 0))

    def test_unsafe_destinations(self):
        with self.assertRaises(CleanupError):
            apply_plan("src", "src/new", Plan())
        with self.assertRaises(CleanupError):
            apply_plan("src", "src", Plan())
        with self.assertRaises(CleanupError):
            apply_plan("missing", "out", Plan())
        with self.assertRaises(CleanupError):
            apply_plan("src", os.path.join("OneDrive - Org", "new"), Plan())
        r = apply_plan("src", os.path.join("OneDrive - Org", "new"), Plan(), allow_synced=True)
        self.assertTrue(r.warnings)

    def test_sibling_with_same_prefix_is_not_inside_source(self):
        apply_plan("src", "src_new", plan_of(("a.txt", "a.txt", "keep")), go=True)  # must not raise
        self.assertTrue(os.path.isfile(os.path.join("src_new", "a.txt")))
