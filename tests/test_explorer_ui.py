"""Browser test: decide in the real explorer page, export the plan, copy with `apply`.

Skipped when Playwright or the explorer files are not available. To run it:
    pip install playwright && playwright install chromium
Set CHROMIUM_PATH to use a browser you already have.
"""
import os
import subprocess
import sys
import unittest

from file_cleanup_tool.explorer import explorer_available

from .helpers import TempCase

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
CHROME = os.environ.get("CHROMIUM_PATH")


def cli(*args, cwd):
    env = dict(os.environ, PYTHONPATH=SRC)
    return subprocess.run([sys.executable, "-m", "file_cleanup_tool", *args], cwd=cwd, env=env, capture_output=True, text=True)


@unittest.skipIf(sync_playwright is None, "playwright not installed")
@unittest.skipUnless(explorer_available(), "explorer files are not in the package")
class ExplorerExportThenApply(TempCase):
    def test_export_drives_apply(self):
        self.assertEqual(cli("demo", "src", cwd=self.t).returncode, 0)
        self.assertEqual(cli("explore", "src", "--no-open", cwd=self.t).returncode, 0)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch()
            pg = b.new_page(viewport={"width": 1500, "height": 860}, accept_downloads=True)
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto("file://" + self.path("cleanup-output", "explorer.html"))
            pg.fill("#nameInput", "Tester")
            pg.click("#nameOk")
            pg.evaluate("""()=>{const m=__S.mine;const d=(p,d,dest)=>{m[p]={d,dest:dest||'',note:'',t:Date.now()}};
              d('Finance\\\\Budget 2023.xlsx','keep');d('Finance\\\\Old','archive');d('Misc\\\\stuff.txt','delete');
              d('Reports','move','Reports\\\\2025');d('readme.txt','discuss');}""")
            with pg.expect_download() as dl:
                pg.click("#btnExport")
            dl.value.save_as(self.path("cleanup_action_plan.csv"))
            b.close()
        self.assertEqual(errors, [])
        r = cli("apply", "--src", "src", "--dest", "out", "--plan", "cleanup_action_plan.csv", "--go", cwd=self.t)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for rel in ("Finance/Budget 2023.xlsx", "Archive/Finance/Old/Budget 2021.xlsx", "Reports/2025/Reports/Q1 report.docx"):
            self.assertTrue(os.path.isfile(self.path("out", *rel.split("/"))), rel)
        self.assertFalse(os.path.exists(self.path("out", "Misc", "stuff.txt")))
        self.assertFalse(os.path.exists(self.path("out", "readme.txt")))


if __name__ == "__main__":
    unittest.main()
