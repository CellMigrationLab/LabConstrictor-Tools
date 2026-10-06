"""CLI robustness: support bundle contents, doctor with broken apps, results folders, duplicate arguments."""

import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401  (must come first)
from test_cli_and_registry import cli, register

from labconstrictor_tools import cli as lc_cli
from labconstrictor_tools import registry


class PrivateHome(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))
        self._saved = os.environ.get("LC_HOME"), os.environ.get("LC_APPS_PATH")
        os.environ["LC_HOME"], os.environ["LC_APPS_PATH"] = str(self.home), ""

    def tearDown(self):
        for key, value in zip(("LC_HOME", "LC_APPS_PATH"), self._saved):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@unittest.skipIf(os.name != "posix", "symlinks")
class SupportBundle(PrivateHome):
    def test_a_symlink_is_never_followed_into_the_zip(self):
        secret = self.home / "secret.txt"
        secret.write_text("TOP-SECRET-KEY")
        (self.home / "apps").mkdir()
        (self.home / "apps" / "good.json").write_text("{}")
        (self.home / "apps" / "debug-key").symlink_to(secret)  # not a *.json either
        (self.home / "apps" / "sneaky.json").symlink_to(secret)  # looks right, points elsewhere
        (self.home / "logs").mkdir()
        (self.home / "logs" / "labconstrictor.log").write_text("a log line")
        (self.home / "runs" / "20200101").mkdir(parents=True)
        (self.home / "runs" / "20200101" / "run.json").write_text("{}")
        (self.home / "runs" / "20200101" / "linked.json").symlink_to(secret)
        out = self.home / "bundle.zip"
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            lc_cli.cmd_support_bundle(argparse.Namespace(out=str(out)))
        with zipfile.ZipFile(out) as bundle:
            names = bundle.namelist()
            everything = b"".join(bundle.read(n) for n in names)
        self.assertNotIn(b"TOP-SECRET-KEY", everything)
        self.assertIn("apps/good.json", names)
        self.assertIn("logs/labconstrictor.log", names)
        self.assertIn("runs/20200101/run.json", names)
        self.assertNotIn("apps/sneaky.json", names)
        self.assertIn("skipped.txt", names)
        self.assertIn("left 3 item(s) out", stderr.getvalue())


class Doctor(PrivateHome):
    ENTRY = {"python": "/nonexistent/python", "module": "m", "pythonpath": [], "runtime_path": ""}

    def diagnose(self, live):
        with (
            mock.patch.object(
                registry, "load_entries", return_value=({"a": self.ENTRY, "b": self.ENTRY}, [])
            ),
            mock.patch.object(registry, "schema", return_value={"tools": []}),
            mock.patch.object(lc_cli, "_live_schema", side_effect=live),
        ):
            return lc_cli.diagnose()

    def test_one_app_that_hangs_or_fails_strangely_does_not_stop_the_others(self):
        silent = subprocess.CompletedProcess([], 1, stdout="", stderr="")
        junk = subprocess.CompletedProcess([], 0, stdout="hello before the schema\n{}", stderr="")
        fine = subprocess.CompletedProcess([], 0, stdout='{"protocol": 1, "tools": []}', stderr="")
        cases = [
            (subprocess.TimeoutExpired("x", 120), "did not answer"),
            (OSError("no such interpreter"), "no such interpreter"),
            ((silent, 0.1), "no error output"),
            ((junk, 0.1), "JSONDecodeError"),
        ]
        for first, expected in cases:
            findings = self.diagnose([first, (fine, 0.1)])
            self.assertEqual([f[0] for f in findings], ["a", "b"], expected)  # app b was still diagnosed
            self.assertEqual(findings[0][1], "error")
            self.assertIn(expected, findings[0][2])
            self.assertNotEqual(findings[1][1], "error")


class ResultsFolders(PrivateHome):
    def test_two_runs_in_the_same_second_get_different_folders(self):
        with mock.patch.object(lc_cli.time, "strftime", return_value="20240101T000000"):
            first = lc_cli._new_results_dir("app", "tool")
            second = lc_cli._new_results_dir("app", "tool")
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_dir() and second.is_dir())

    def test_only_folders_this_command_made_are_pruned(self):
        base = self.home / "results"
        base.mkdir()
        (base / "000_keep").mkdir()
        (base / "000_keep" / "mine.txt").write_text("precious")
        for i in range(25):
            (base / ("20200101T0000%02d_x" % i)).mkdir()
        lc_cli._new_results_dir("app", "tool")
        self.assertEqual((base / "000_keep" / "mine.txt").read_text(), "precious")
        made = [p for p in base.iterdir() if re.match(r"\d{8}T\d{6}_", p.name)]
        self.assertEqual(len(made), lc_cli.RESULTS_KEPT)

    def test_a_tool_name_with_separators_cannot_leave_the_results_folder(self):
        folder = lc_cli._new_results_dir("../../app", "../../../outside")
        self.assertEqual(folder.resolve().parent, (self.home / "results").resolve())
        self.assertNotIn("/", folder.name)


class ClosedPipe(PrivateHome):
    def test_output_to_a_reader_that_went_away_is_not_a_traceback(self):
        """`list | head`, or a pager that was quit: the command ends quietly."""
        register(self.home, "synthetic")
        read_end, write_end = os.pipe()
        os.close(read_end)  # nobody reads: every write fails with EPIPE
        done = subprocess.run(
            [sys.executable, "-c", "import sys; from labconstrictor_tools.__main__ import main; sys.exit(main(['list']))"],
            stdout=write_end, stderr=subprocess.PIPE, text=True,
            env={**os.environ, "LC_HOME": str(self.home), "LC_APPS_PATH": "", "PYTHONPATH": str(_paths.ROOT)},
        )  # fmt: skip
        os.close(write_end)
        self.assertEqual(done.stderr, "")
        self.assertEqual(done.returncode, 0)


class Arguments(PrivateHome):
    def test_a_parameter_given_twice_is_refused(self):
        register(self.home, "synthetic")
        done = cli("run", "synthetic", "scalar_echo", "a=1", "a=10", home=self.home)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("more than once", done.stderr)

    def test_a_sample_given_twice_is_refused(self):
        with self.assertRaises(SystemExit) as caught:
            lc_cli.cmd_test(
                argparse.Namespace(
                    sample=["image=a.tif", "image=b.tif"], cases=None, module="m", pythonpath=[], only=None, timeout=1,
                    check_cancel=False, python=None, json=False,
                )  # fmt: skip
            )
        self.assertIn("more than once", str(caught.exception))

    def test_a_numeric_choice_is_sent_as_a_number(self):
        param = {"name": "mode", "type": "choice", "choices": [1, 2]}
        self.assertEqual(lc_cli.parse_value(param, "1"), 1)
        self.assertEqual(lc_cli.parse_value({"name": "m", "type": "choice", "choices": ["a", "b"]}, "b"), "b")
        self.assertEqual(lc_cli.parse_value(param, "7"), "7")  # not a choice: the worker will say so

    def test_indeterminate_progress_is_not_shown_as_zero_percent(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            lc_cli._print_progress("loading", None)
            lc_cli._print_progress("half", 0.5)
        self.assertEqual(stderr.getvalue().splitlines(), ["[ ?%] loading", "[ 50%] half"])


class FailedRunLeavesNoEmptyFolder(PrivateHome):
    def test_a_failed_run_does_not_leave_an_empty_results_folder(self):
        register(self.home, "synthetic")
        done = cli(
            "run", "synthetic", "image_stats", "image=/nonexistent/none.tif", "--no-record", home=self.home
        )
        self.assertIn('"status": "FAILED"', done.stdout)
        results = self.home / "results"
        self.assertEqual(list(results.iterdir()) if results.exists() else [], [])
        ok = cli(
            "run", "synthetic", "scalar_echo", "a=1", "b=2", "--no-record", home=self.home
        )  # a good run keeps its folder
        self.assertIn('"status": "COMPLETE"', ok.stdout)
        self.assertEqual(len(list(results.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
