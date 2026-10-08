"""Guards for the bugs in docs/REGRESSION_LEDGER.md that no other test pins down, and a check that the ledger itself is true:
every test it names as a guard exists."""

import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

LEDGER = ROOT / "docs" / "REGRESSION_LEDGER.md"
TOOLS_APP = Path(__file__).resolve().parent / "failure_app"


class NonUtf8Line(unittest.TestCase):
    """2026-10-08, macOS: a request line that was not valid UTF-8 killed the worker's reader on a strict-UTF-8 stdin."""

    def test_a_line_that_is_not_utf8_is_skipped_and_the_next_task_still_runs(self):
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(ROOT), str(TOOLS_APP)]),
            "PYTHONIOENCODING": "utf-8:strict",  # the strict decoding of macOS, on every platform
            "LC_HOME": tempfile.mkdtemp(),
        }
        proc = subprocess.Popen(
            [sys.executable, "-m", "labconstrictor_tools", "serve", "--module", "failure_tools"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        )  # fmt: skip
        try:
            request = json.dumps(
                {"task": "t1", "requestType": "EXECUTE", "script": "lc:echo", "inputs": {}}
            ).encode()
            proc.stdin.write(b'{"task": "bad", "x": "\xff\xfe\xc3("}\n' + b"\xff\xfe\xfd\n" + request + b"\n")
            proc.stdin.flush()
            seen = []
            end = time.time() + 30
            while time.time() < end:
                line = proc.stdout.readline()
                if not line:
                    break
                message = json.loads(line)
                seen.append(message["responseType"])
                if message["responseType"] in ("COMPLETION", "FAILURE"):
                    break
            self.assertIn("LAUNCH", seen, "the reader died on the bad line: the next request was never read")
            self.assertEqual(seen[-1], "COMPLETION")
        finally:
            proc.stdin.close()
            proc.wait(30)
            proc.stdout.close()
            proc.stderr.close()


class BrokenPipeOnExit(unittest.TestCase):
    """2026-10-08: `labconstrictor-tools ... | head` printed a traceback when the buffered output was flushed at exit."""

    def test_the_reader_of_the_output_going_away_is_not_an_error(self):
        env = {**os.environ, "PYTHONPATH": str(ROOT), "LC_HOME": tempfile.mkdtemp(), "LC_APPS_PATH": ""}
        proc = subprocess.Popen(
            [sys.executable, "-m", "labconstrictor_tools", "doctor", "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        )  # fmt: skip
        proc.stdout.close()  # the reader leaves before the first byte is written
        try:
            error = proc.stderr.read().decode("utf-8", errors="replace")
            code = proc.wait(60)
        finally:
            proc.stderr.close()
        self.assertEqual(code, 0, error)
        self.assertNotIn("Traceback", error)
        self.assertNotIn("BrokenPipeError", error)


def ledger_guards():
    """Every `tests/<file>.py::<Class>.<method>` named in the ledger's guard column."""
    text = LEDGER.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"`(test_[a-z0-9_]+\.py)::([A-Za-z0-9_]+)\.([a-z0-9_]+)`", text)))


class TheLedgerIsTrue(unittest.TestCase):
    def test_every_guard_named_in_the_ledger_exists(self):
        guards = ledger_guards()
        self.assertGreaterEqual(len(guards), 4)
        for file, cls, method in guards:
            with self.subTest("%s::%s.%s" % (file, cls, method)):
                module = importlib.import_module(file[:-3])
                self.assertTrue(callable(getattr(getattr(module, cls), method, None)))

    def test_the_four_seed_bugs_are_in_the_ledger(self):
        text = LEDGER.read_text(encoding="utf-8").lower()
        for fragment in ("job object", "utf-8", "broken pipe", "cancel"):
            self.assertIn(fragment, text)

    def test_every_row_has_five_cells(self):
        rows = [r for r in LEDGER.read_text(encoding="utf-8").splitlines() if r.startswith("| 20")]
        self.assertGreaterEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(len([c for c in row.strip("|").split("|") if c.strip()]), 5, row)


if __name__ == "__main__":
    unittest.main()
