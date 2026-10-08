"""When something goes wrong, the error shown to the user and the log file must say what, where and why."""

import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import V3

from labconstrictor_tools import client, log

APPS = V3 / "tests"


def run_tool(module_dir, tool, **kw):
    with client.WorkerProcess(module="tools", pythonpath=[str(APPS / module_dir)], **kw) as worker:
        return worker.task(tool, {}).wait(60), "".join(worker.stderr)


class FailureDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="lchome_")
        os.environ["LC_HOME"] = cls.home
        log._logger = None  # re-open the log in the temporary home

    def test_import_error_shows_traceback_and_context(self):
        task, _ = run_tool("import_error_app", "never")
        self.assertEqual(task.status, "CRASHED")
        self.assertIn("a_package_that_is_not_installed", task.error)
        self.assertIn("cannot import tool module 'tools'", task.error)
        self.assertIn("ModuleNotFoundError", task.error)
        self.assertIn("package is missing", task.error)  # hint

    @unittest.skipUnless(os.name == "posix", "a SIGKILL exit code (-9) does not exist on Windows")
    def test_killed_worker_is_explained(self):
        task, _ = run_tool("crashy_app", "killed")
        self.assertEqual(task.status, "CRASHED")
        self.assertIn("code -9", task.error)
        self.assertIn("out of memory", task.error)

    def test_missing_interpreter_is_explained(self):
        with self.assertRaises(client.WorkerStartError) as caught:
            run_tool("crashy_app", "raises", python="/nonexistent/prefix/bin/python")
        self.assertIn("was not found at /nonexistent/prefix/bin/python", str(caught.exception))
        self.assertIn("labconstrictor.log", str(caught.exception))

    def test_log_records_the_story_with_traceback(self):
        task, stderr = run_tool("crashy_app", "raises")
        self.assertEqual(task.status, "FAILED")
        self.assertIn("ZeroDivisionError", task.traceback)
        text = log.log_path().read_text(encoding="utf-8")
        for expected in (
            "session start",
            "worker started",
            "task %s start tool=raises" % task.id[:8],
            "task %s FAILED" % task.id[:8],
            "ZeroDivisionError",
            "worker[",  # the worker's stderr is in the same file
        ):
            self.assertIn(expected, text)

    def test_support_bundle_and_logs_command(self):
        import subprocess
        import sys

        env = {**os.environ, "LC_HOME": self.home, "PYTHONPATH": str(V3)}
        out = Path(self.home) / "bundle.zip"
        run = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "support-bundle", "--out", str(out)],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        names = zipfile.ZipFile(out).namelist()
        self.assertIn("doctor.txt", names)
        self.assertIn("environment.txt", names)
        self.assertTrue(any(n.startswith("logs/labconstrictor.log") for n in names), names)
        shown = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "logs", "-n", "5"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(shown.returncode, 0)
        path = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "logs", "--path"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertTrue(path.stdout.strip().endswith("labconstrictor.log"))
        json.dumps(names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
