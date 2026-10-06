"""The author's test harness must not green-light what it did not check: misspelled expectations, truncated matrices,
directories as files, string inputs turned into paths, describe output polluted by prints, cancel checks without a verdict.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import client, testing


def write(directory, name, text):
    path = Path(directory) / name
    path.write_text(text)
    return path


class CasesFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_misspelled_expectation_keys_are_rejected_at_every_level(self):
        path = write(self.dir, "cases.json", json.dumps([
            {"tool": "t", "expect": {"max_secods": 0, "results": {"table": {"row": 999}}}, "inptus": {}},
            {"tool": "t", "expect": {"progress_events": 3}},
        ]))  # fmt: skip
        with self.assertRaises(ValueError) as caught:
            testing.load_cases(path)
        text = str(caught.exception)
        self.assertIn("'max_secods'", text)
        self.assertIn("'inptus'", text)
        self.assertIn("'progress_events'", text)
        self.assertIn("case 1", text)  # every problem is listed, not only the first

    def test_a_result_expectation_with_an_unknown_key_is_a_problem_not_a_pass(self):
        result = {"name": "table", "type": "table", "path": str(write(self.dir, "t.csv", "a,b\n1,2\n"))}
        problems = testing.expectation_problems({"results": {"table": {"row": 999}}}, [result], 0.1, 0)
        self.assertEqual(len(problems), 1)
        self.assertIn("unknown expectation 'row'", problems[0])
        self.assertEqual(
            testing.expectation_problems({"results": {"table": {"rows": 1}}}, [result], 0.1, 0), []
        )

    def test_a_valid_file_still_loads_in_both_layouts(self):
        case = {
            "tool": "t",
            "inputs": {"x": 1},
            "expect": {"status": "COMPLETE", "max_seconds": 5},
            "comment": "ok",
        }
        self.assertEqual(len(testing.load_cases(write(self.dir, "a.json", json.dumps([case])))), 1)
        self.assertEqual(len(testing.load_cases(write(self.dir, "b.json", json.dumps({"cases": [case]})))), 1)

    def test_a_text_parameter_is_never_turned_into_a_path(self):
        (Path(self.dir) / "default").write_text("a file that happens to have this name")
        tool = {"id": "t", "inputs": [
            {"name": "model", "type": "string", "required": False, "label": "m"},
            {"name": "image", "type": "image", "required": True, "label": "i"},
        ], "outputs": []}  # fmt: skip
        write(self.dir, "a.tif", "x")
        case = {"tool": "t", "inputs": {"model": "default", "image": "a.tif"}, "_dir": self.dir}
        inputs = testing._resolve_paths(case, tool)
        self.assertEqual(inputs["model"], "default")
        self.assertEqual(inputs["image"], str(Path(self.dir, "a.tif").resolve()))


class Contracts(unittest.TestCase):
    def test_a_directory_is_not_a_file_output(self):
        problems = testing._result_problems({"type": "file", "name": "report", "path": tempfile.gettempdir()})
        self.assertEqual(len(problems), 1)
        self.assertIn("directory", problems[0])
        existing = write(tempfile.mkdtemp(), "r.txt", "x")
        self.assertEqual(
            testing._result_problems({"type": "file", "name": "report", "path": str(existing)}), []
        )

    def test_an_affine_expectation_must_be_3x3_and_is_compared_in_full(self):
        result = {"type": "affine", "name": "a", "matrix_yx": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        short = testing._compare("a", result, {"matrix": [[1, 0, 0]]})
        self.assertEqual(len(short), 1)
        self.assertIn("3x3", short[0])
        self.assertEqual(testing._compare("a", result, {"matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}), [])
        self.assertEqual(len(testing._compare("a", result, {"matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 2]]})), 1)


class CancelCheck(unittest.TestCase):
    TOOL = {"id": "t", "inputs": [], "outputs": []}

    def run_check(self, task):
        class FakeWorker:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def task(self, tool_id, inputs):
                self.inputs = inputs
                return task

            def kill(self):
                self.killed = True

        worker = FakeWorker()
        with (
            mock.patch.object(client, "WorkerProcess", return_value=worker),
            mock.patch.object(testing.time, "sleep"),
        ):
            return testing._cancel_check(self.TOOL, {"tool": "t"}, {}), worker

    def test_a_tool_that_ignores_cancel_fails_the_check(self):
        task = mock.Mock()
        task.done.is_set.return_value = False
        task.wait.side_effect = lambda *_: None
        (problems, warnings), worker = self.run_check(task)
        self.assertEqual(len(problems), 1)
        self.assertIn("ignored a cancel request", problems[0])
        self.assertEqual(warnings, [])
        self.assertTrue(worker.killed)

    def test_the_auxiliary_run_gets_its_own_job_folder(self):
        task = mock.Mock()
        task.done.is_set.return_value = True  # finished before the cancel: nothing to learn
        (problems, warnings), worker = self.run_check(task)
        self.assertEqual((problems, warnings), ([], []))
        self.assertIn("_job_dir", worker.inputs)
        self.assertFalse(
            Path(worker.inputs["_job_dir"]).parent.exists()
        )  # and the scratch folder is gone again


class DescribeOutput(unittest.TestCase):
    def test_prints_while_importing_do_not_reach_stdout(self):
        directory = tempfile.mkdtemp()
        write(directory, "chatty_lc_tools.py", "print('initialising')\nfrom labconstrictor_tools import Scalars, tool\n"
              "@tool('X')\ndef x() -> Scalars:\n    return {}\n")  # fmt: skip
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(_paths.ROOT), directory]),
            "LC_HOME": tempfile.mkdtemp(),
        }
        done = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "describe", "--module", "chatty_lc_tools"],
            capture_output=True, text=True, env=env,
        )  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(
            json.loads(done.stdout)["tools"][0]["id"], "x"
        )  # stdout is exactly one JSON document
        self.assertIn("initialising", done.stderr)  # not lost: it went to stderr


class CliMessage(unittest.TestCase):
    def test_an_invalid_cases_file_is_reported_without_a_traceback(self):
        path = write(tempfile.mkdtemp(), "cases.json", json.dumps([{"tool": "t", "expect": {"typo": 1}}]))
        done = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "test", "--module", "labconstrictor_tools.examples.synthetic",
             "--cases", str(path)],
            capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(_paths.ROOT), "LC_HOME": tempfile.mkdtemp()},
        )  # fmt: skip
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("unknown expectation 'typo'", done.stderr)
        self.assertNotIn("Traceback", done.stderr)


if __name__ == "__main__":
    unittest.main()
