"""2026-10-12 (issue #49): `register` stored a relative --prefix / --pythonpath as typed, so the app vanished from `list` (or
imported other code) when a host started from another folder. Real command line, two different working directories.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import GENERIC_PREFIX, ROOT

MODULE = "relpath_tools"
SOURCE = """from labconstrictor_tools import Scalars, tool


@tool("Where the code came from")
def origin(x: float = 1.0) -> Scalars:
    return {"x": x, "marker": 4242.0}
"""


def lc(*args, home, cwd):
    env = {**os.environ, "LC_HOME": str(home), "LC_APPS_PATH": "", "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, "-m", "labconstrictor_tools", *args],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(cwd),
    )  # fmt: skip


class RelativeRegistration(unittest.TestCase):
    def test_a_relative_prefix_and_pythonpath_still_work_from_another_folder(self):
        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        folder_a = Path(tempfile.mkdtemp(prefix="lc_a_")).resolve()
        folder_b = Path(tempfile.mkdtemp(prefix="lc_b_")).resolve()
        (folder_a / "src").mkdir()
        (folder_a / "src" / (MODULE + ".py")).write_text(SOURCE, encoding="utf-8")
        relative_prefix = os.path.relpath(
            GENERIC_PREFIX, folder_a
        )  # what a person types: "../../usr/..." or ".venv"
        self.assertFalse(os.path.isabs(relative_prefix))

        done = lc(
            "register", "--name", "relapp", "--prefix", relative_prefix, "--module", MODULE,
            "--pythonpath", "src", home=home, cwd=folder_a,
        )  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)

        stored = json.loads((home / "apps" / "relapp.json").read_text(encoding="utf-8"))
        for path in (stored["prefix"], stored["python"], *stored["pythonpath"]):
            self.assertTrue(os.path.isabs(path), "stored %r depends on the working directory" % path)
        self.assertEqual(stored["pythonpath"], [str(folder_a / "src")])

        listed = json.loads(lc("list", "--json", home=home, cwd=folder_b).stdout)
        self.assertEqual([t["id"] for t in listed["apps"]["relapp"]["tools"]], ["origin"])
        doctor = lc("doctor", "--json", home=home, cwd=folder_b)
        self.assertNotIn("not available on this machine", doctor.stdout + doctor.stderr)
        ran = lc("run", "relapp", "origin", "x=3", home=home, cwd=folder_b)
        self.assertEqual(ran.returncode, 0, ran.stderr)
        report = json.loads(ran.stdout)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(
            report["results"][0]["values"], {"x": 3.0, "marker": 4242.0}
        )  # the code in folder_a/src ran

        # unregister --prefix compares equivalent paths: the same install typed relatively from folder A matches
        gone = lc("unregister", "--name", "relapp", "--prefix", relative_prefix, home=home, cwd=folder_a)
        self.assertEqual(gone.returncode, 0, gone.stderr)
        self.assertFalse((home / "apps" / "relapp.json").exists())


if __name__ == "__main__":
    unittest.main()
