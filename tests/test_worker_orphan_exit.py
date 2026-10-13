"""`Worker._orphan_exit`: the host is gone, so the worker leaves. A temp folder it could not remove is said in the log file
(stderr has no reader any more), and the worker leaves anyway.
"""

import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import worker


class OrphanExit(unittest.TestCase):
    def leave(self, folders, *, removed):
        instance = worker.Worker.__new__(worker.Worker)
        instance._owned_dirs = set(folders)
        calls = []
        rmtree = (lambda path, ignore_errors=False: Path(path).rmdir()) if removed else (lambda *a, **k: None)
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"LC_HOME": home}):
            with (
                mock.patch.object(worker.shutil, "rmtree", rmtree),
                mock.patch.object(worker.Worker, "_end_process_group"),
                mock.patch.object(worker.os, "_exit", lambda code: calls.append(code)),
                self.assertLogs("labconstrictor", "DEBUG") as logged,
            ):
                logging.getLogger("labconstrictor").debug("marker")
                instance._orphan_exit()
        return calls, [r.getMessage() for r in logged.records if r.levelno >= logging.WARNING]

    def test_a_folder_that_cannot_be_removed_is_logged_and_the_worker_still_leaves(self):
        with tempfile.TemporaryDirectory() as parent:
            stuck = Path(parent) / "lcjob_stuck"
            stuck.mkdir()
            calls, warnings = self.leave([stuck], removed=False)
        self.assertEqual(calls, [1])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn(str(stuck), warnings[0])

    def test_a_removed_folder_is_not_mentioned(self):
        with tempfile.TemporaryDirectory() as parent:
            gone = Path(parent) / "lcjob_gone"
            gone.mkdir()
            calls, warnings = self.leave([gone], removed=True)
        self.assertEqual((calls, warnings), ([1], []))


if __name__ == "__main__":
    unittest.main()
