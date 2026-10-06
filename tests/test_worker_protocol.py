"""Worker protocol robustness: malformed and hostile request lines, tool exits, duplicate ids, oversized lines.
The worker is driven with raw JSON lines (no client), so every case is exactly what a broken host could send.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import protocol

APP = Path(__file__).parent / "protocol_app"


class RawWorker:
    closed_stderr = None

    def __init__(self):
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(_paths.ROOT), str(APP)]),
            "LC_HOME": tempfile.mkdtemp(),
        }
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "labconstrictor_tools", "serve", "--module", "tools"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
        )  # fmt: skip

    def send(self, *lines):
        for line in lines:
            self.proc.stdin.write((line if isinstance(line, str) else json.dumps(line)) + "\n")
        self.proc.stdin.flush()

    def read_until(self, task, timeout=20):
        """Responses for `task` up to and including its terminal one."""
        got, end = [], time.time() + timeout
        while time.time() < end:
            line = self.proc.stdout.readline()
            if not line:
                break
            message = json.loads(line)
            if message["task"] == task:
                got.append(message)
                if message["responseType"] in protocol.TERMINAL:
                    return got
        self.fail_to_finish = got
        raise AssertionError("no terminal response for %r, got %r" % (task, got))

    def close(self):
        if self.closed_stderr is not None:
            return self.closed_stderr
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        err = self.proc.stderr.read()
        self.proc.stdout.close()
        self.proc.stderr.close()
        self.closed_stderr = err
        return err


def execute(task, tool, inputs=None, **extra):
    return {
        "task": task,
        "requestType": "EXECUTE",
        "script": "lc:" + tool,
        "inputs": {} if inputs is None else inputs,
        **extra,
    }


class WorkerProtocol(unittest.TestCase):
    def setUp(self):
        self.w = RawWorker()

    def tearDown(self):
        self.stderr = self.w.close()

    def test_a_tool_calling_sys_exit_gets_a_structured_failure_and_the_worker_lives(self):
        self.w.send(execute("1", "exits"), execute("2", "defaults"))
        failure = self.w.read_until("1")[-1]
        self.assertEqual((failure["responseType"], failure["code"]), ("FAILURE", "SystemExit"))
        self.assertEqual(self.w.read_until("2")[-1]["responseType"], "COMPLETION")

    def test_a_malformed_task_id_does_not_kill_the_reader(self):
        self.w.send(
            {"task": [], "requestType": "EXECUTE", "script": "lc:defaults", "inputs": {}},
            execute("ok", "defaults"),
        )
        self.assertEqual(self.w.read_until("ok")[-1]["responseType"], "COMPLETION")

    def test_inputs_that_are_not_an_object_are_rejected_not_replaced_by_defaults(self):
        for bad in ([], "", 0, False):
            self.w.send(execute("b", "defaults", bad))
            last = self.w.read_until("b")[-1]
            self.assertEqual((last["responseType"], last["code"]), ("FAILURE", "bad_request"), bad)

    def test_a_non_text_script_is_rejected(self):
        self.w.send({"task": "s", "requestType": "EXECUTE", "script": 5, "inputs": {}})
        self.assertEqual(self.w.read_until("s")[-1]["code"], "bad_request")

    def test_a_duplicate_task_id_does_not_corrupt_the_running_task(self):
        self.w.send(execute("d", "waits", {"seconds": 1.5}), execute("d", "defaults"))
        responses = self.w.read_until("d")
        self.assertEqual(
            [r["responseType"] for r in responses], ["LAUNCH", "COMPLETION"]
        )  # one task, one answer
        self.w.send(execute("after", "defaults"))
        self.assertEqual(self.w.read_until("after")[-1]["responseType"], "COMPLETION")
        self.assertIn("still in use", self.w.close())

    def test_a_cancel_for_an_unknown_task_is_reported_and_does_not_cancel_a_later_task(self):
        self.w.send({"task": "A", "requestType": "CANCEL"}, execute("A", "defaults"))
        self.assertEqual(self.w.read_until("A")[-1]["responseType"], "COMPLETION")
        self.assertIn("not running", self.w.close())

    def test_unknown_request_types_and_garbage_lines_are_reported_on_stderr(self):
        self.w.send({"task": "u", "requestType": "EXPLODE"}, "not json", "[1, 2]", execute("ok", "defaults"))
        self.assertEqual(self.w.read_until("ok")[-1]["responseType"], "COMPLETION")
        err = self.w.close()
        for text in ("unknown type", "not JSON", "not an object"):
            self.assertIn(text, err)

    def test_a_result_json_cannot_carry_fails_explicitly_instead_of_becoming_text(self):
        self.w.send(execute("o", "odd"))
        last = self.w.read_until("o")[-1]
        self.assertEqual((last["responseType"], last["code"]), ("FAILURE", "unserializable_result"))

    def test_nan_travels_as_null_as_documented(self):
        self.w.send(execute("n", "nan"))
        last = self.w.read_until("n")[-1]
        self.assertEqual(last["responseType"], "COMPLETION")
        self.assertIsNone(last["outputs"]["results"][0]["values"]["v"])

    def test_no_progress_after_the_terminal_response(self):
        from labconstrictor_tools import runtime

        runtime.install(progress=lambda *a: self.fail("sink must be cleared"))
        runtime.install()
        runtime.progress(0.5, "late")  # no sink installed: harmless


class OversizedLines(unittest.TestCase):
    def test_bounded_lines_drops_an_oversized_line_and_keeps_the_next(self):
        stream = io.StringIO("ok1\n" + "x" * 50 + "\nok2\n" + "y" * 45)
        self.assertEqual(list(protocol._bounded_lines(stream.readline, limit=10)), ["ok1\n", "ok2\n"])

    def test_line_splitter_drops_an_oversized_line_even_across_chunks(self):
        splitter = protocol.LineSplitter(limit=10)
        out = splitter.feed(b"ok1\n" + b"x" * 8)
        out += splitter.feed(b"x" * 8)  # now 16 > limit without newline
        out += splitter.feed(b"xx\nok2\n")
        out += splitter.finish()
        self.assertEqual(out, ["ok1", "ok2"])
        self.assertEqual(protocol.LineSplitter(limit=10).feed(b"abc\ndef"), ["abc"])


if __name__ == "__main__":
    unittest.main()
