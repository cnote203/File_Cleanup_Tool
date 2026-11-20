import csv
import os
import tempfile
import unittest


class TempCase(unittest.TestCase):
    """Each test runs inside its own temporary folder."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.t = self._tmp.name
        self._cwd = os.getcwd()
        os.chdir(self.t)
        self.addCleanup(os.chdir, self._cwd)

    def path(self, *parts):
        return os.path.join(self.t, *parts)

    def write_csv(self, name, header, rows, bom=False):
        p = self.path(name)
        with open(p, "w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        return p

    def make_files(self, files):
        for rel, content in files.items():
            p = self.path(*rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(content if isinstance(content, bytes) else content.encode())


def read_text(path, **kw):
    with open(path, **kw) as f:
        return f.read()
