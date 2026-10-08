"""Failure injection through the real client: a worker killed mid-task, tools that return the wrong thing, raise, hang and are
cancelled, results nobody can serialise, huge results, noise on stdout, a flood on stderr. Each case must end with the documented
status (COMPLETE | FAILED | CANCELED | CRASHED, docs/PROTOCOL.md and client.py) and a message a person can read, and must leave no
process behind: the worker and every process a tool started are gone after `close()`.

The misbehaving tools are in failure_app/failure_tools.py (only the tools are test code; worker, client and converters are the
production ones).
"""

import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
import psutil
from roundtrip_known_failures import is_known

from labconstrictor_tools import client
from labconstrictor_tools.client import WorkerProcess

APP_DIR = Path(__file__).resolve().parent / "failure_app"
MODULE = "failure_tools"
TOOLERROR_WORD = re.compile(r"^[a-z][a-z0-9_]*$")
FLOOD_MB = 10
HUGE_MB = 40


def start():
    return WorkerProcess(module=MODULE, pythonpath=[str(APP_DIR)])


def alive(pid):
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def wait_for(condition, seconds=10.0):
    end = time.time() + seconds
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.05)
    return bool(condition())


def child_pid(path, seconds=15.0):
    wait_for(lambda: Path(path).exists() and Path(path).read_text().strip(), seconds)
    return int(Path(path).read_text())


def run_tool(tool_id, inputs=None, timeout=90):
    """One task on a fresh worker, then close: (task, worker)."""
    worker = start()
    try:
        task = worker.task(tool_id, inputs or {}).wait(timeout)
    finally:
        worker.close()
    return task, worker


def toolerror_problems(tool_id, inputs=None):
    """The task must FAIL with a ToolError code (not the name of a Python exception) and a message."""
    task, _ = run_tool(tool_id, inputs)
    problems = []
    if task.status != "FAILED":
        return ["status %s, expected FAILED" % task.status]
    if not (task.code and TOOLERROR_WORD.match(task.code)):
        problems.append(
            "code %r is a Python exception class, not a ToolError code (%s)"
            % (task.code, (task.error or "")[:120])
        )
    return problems


def task_on_dead_worker_problems():
    """After the worker has died, asking it for another task gives a CRASHED task, not an exception in the host."""
    worker = start()
    try:
        worker.task("crash_mid_task", {}).wait(30)
        try:
            task = worker.task("echo", {})
        except OSError as error:
            return ["task() raised %s: %s" % (type(error).__name__, error)]
        if not task.wait(10).done.is_set() or task.status != "CRASHED":
            return ["the task on a dead worker ended as %s" % task.status]
        return []
    finally:
        worker.close()


def progress_problems():
    """Progress is shown as a whole percent: 0.29 must arrive as 29 %, not 28 % (the fraction is what the tool reported)."""
    seen = []
    worker = start()
    problems = []
    try:
        for k in range(101):
            seen.clear()
            task = worker.task(
                "report_progress", {"fraction": k / 100}, on_update=lambda m, f: seen.append(f)
            ).wait(30)
            if task.status != "COMPLETE" or len(seen) != 1:
                return ["progress %d: %s, %d updates" % (k, task.status, len(seen))]
            if seen[0] != k / 100:
                problems.append("progress(%s) arrived as %s" % (k / 100, seen[0]))
    finally:
        worker.close()
    return problems


def children_problems():
    """The host goes away (its end of the pipe closes) while a tool runs: nothing the tool started may keep running."""
    with tempfile.TemporaryDirectory() as folder:
        pid_file = str(Path(folder) / "child.pid")
        worker = start()
        try:
            task = worker.task("hang", {"child_pid_file": pid_file})
            task.launched.wait(30)
            child = child_pid(pid_file)
            worker.proc.stdin.close()
            worker.proc.wait(30)
            gone = wait_for(lambda: not alive(child), 5.0)
            return (
                []
                if gone
                else ["the worker exited but the process its tool started (pid %d) is still running" % child]
            )
        finally:
            worker.kill()
            try:
                if alive(child):
                    psutil.Process(child).kill()
            except (psutil.NoSuchProcess, NameError):
                pass


class Crashes(unittest.TestCase):
    def test_a_worker_that_exits_mid_task_gives_crashed_with_its_exit_code(self):
        task, worker = run_tool("crash_mid_task", {"how": "exit"})
        self.assertEqual(task.status, "CRASHED")
        self.assertIn("worker exited unexpectedly (code 7)", task.error)
        self.assertIsNotNone(worker.proc.poll())

    @unittest.skipUnless(os.name == "posix", "SIGKILL")
    def test_a_killed_worker_says_it_was_killed(self):
        task, _ = run_tool("crash_mid_task", {"how": "kill"})
        self.assertEqual(task.status, "CRASHED")
        self.assertIn("code -9", task.error)
        self.assertIn("killed", task.error)

    def test_progress_before_the_crash_reached_the_host_and_the_other_tasks_are_unaffected(self):
        seen = []
        worker = start()
        try:
            crashed = worker.task(
                "crash_mid_task", {}, on_update=lambda message, fraction: seen.append((message, fraction))
            ).wait(30)
            self.assertEqual(crashed.status, "CRASHED")
            self.assertEqual(seen, [("halfway", 0.5)])
            self.assertFalse(worker.alive)
        finally:
            worker.close()

    def test_a_worker_killed_from_outside_mid_task(self):
        with tempfile.TemporaryDirectory() as folder:
            pid_file = str(Path(folder) / "c.pid")
            worker = start()
            try:
                task = worker.task("hang", {"child_pid_file": pid_file})
                task.launched.wait(30)
                child = child_pid(pid_file)
                worker.kill()
                task.wait(20)
                self.assertEqual(task.status, "CRASHED")
                self.assertIn("worker exited unexpectedly", task.error)
                self.assertTrue(
                    wait_for(lambda: not alive(child), 5.0), "the tool's child process is still running"
                )
                self.assertIsNotNone(worker.proc.poll())
            finally:
                worker.close()

    def test_no_process_is_left_after_a_crash_and_close(self):
        with tempfile.TemporaryDirectory() as folder:
            pid_file = str(Path(folder) / "c.pid")
            worker = start()
            task = worker.task("crash_mid_task", {"child_pid_file": pid_file}).wait(30)
            self.assertEqual(task.status, "CRASHED")
            child = child_pid(pid_file)
            worker.close()
            self.assertTrue(
                wait_for(lambda: not alive(child), 5.0), "the child of the crashed tool survived close()"
            )
            self.assertIsNotNone(worker.proc.poll())

    def test_asking_a_dead_worker_for_a_task_gives_a_crashed_task(self):
        if is_known("lifecycle:task_on_a_dead_worker"):
            self.skipTest("known failure F17, watched by test_roundtrip_known_failures")
        self.assertEqual(task_on_dead_worker_problems(), [])


class WhatAToolRaises(unittest.TestCase):
    def test_a_tool_error_arrives_with_its_code_and_text(self):
        task, _ = run_tool("raise_tool_error")
        self.assertEqual(task.status, "FAILED")
        self.assertEqual(task.code, "my_code")
        self.assertEqual(task.error, "[my_code] a readable message with unicode é and a second\nline")
        self.assertIsNone(task.traceback)

    def test_an_unexpected_exception_arrives_with_its_name_text_and_traceback(self):
        task, worker = run_tool("raise_unexpected", {"kind": "zero"})
        self.assertEqual((task.status, task.code), ("FAILED", "ZeroDivisionError"))
        self.assertIn("ZeroDivisionError", task.error)
        self.assertIn("raise_unexpected", task.traceback)
        self.assertIn("ZeroDivisionError", "".join(worker.stderr))

    def test_exceptions_with_awkward_text_arrive_unchanged(self):
        task, _ = run_tool("raise_unexpected", {"kind": "multiline"})
        self.assertEqual(task.error, "[RuntimeError] first line\nsecond line µm\n\ttabbed")

    def test_memory_error_and_exits_do_not_take_the_worker_down(self):
        worker = start()
        try:
            for kind, code in (
                ("memory", "MemoryError"),
                ("system_exit", "SystemExit"),
                ("keyboard", "KeyboardInterrupt"),
            ):
                task = worker.task("raise_unexpected", {"kind": kind}).wait(30)
                self.assertEqual((task.status, task.code), ("FAILED", code), kind)
                self.assertTrue(worker.alive, kind)
            self.assertEqual(
                worker.task("echo", {"value": 9}).wait(30).outputs["results"][0]["values"], {"value": 9}
            )
        finally:
            worker.close()

    def test_failures_leave_no_job_folder_behind(self):
        task, _ = run_tool("raise_unexpected", {"kind": "zero"})
        self.assertEqual(task.status, "FAILED")
        self.assertFalse(task.outputs)


class WhatAToolReturns(unittest.TestCase):
    def test_the_wrong_number_of_values_is_bad_return_with_both_counts(self):
        for tool_id, got in (
            ("wrong_count_too_few", 1),
            ("wrong_count_too_many", 3),
            ("wrong_count_none", 0),
        ):
            with self.subTest(tool_id):
                task, _ = run_tool(tool_id)
                self.assertEqual((task.status, task.code), ("FAILED", "bad_return"))
                self.assertEqual(task.error, "[bad_return] tool returned %d values, declared 2" % got)

    def test_the_wrong_type_fails_with_a_message_and_the_worker_survives(self):
        worker = start()
        try:
            for tool_id in (
                "wrong_type_image",
                "wrong_type_table",
                "wrong_type_scalars",
                "wrong_type_points",
                "wrong_count_one_array",
                "wrong_count_tuple_for_one",
            ):
                with self.subTest(tool_id):
                    task = worker.task(tool_id, {}).wait(30)
                    self.assertEqual(task.status, "FAILED")
                    self.assertTrue(task.error and task.error.strip())
                    self.assertTrue(worker.alive)
                    self.assertEqual(worker.task("echo", {}).wait(30).status, "COMPLETE")
        finally:
            worker.close()

    def test_the_wrong_type_is_reported_with_a_tool_error_code(self):
        for tool_id in (
            "wrong_type_image",
            "wrong_type_table",
            "wrong_type_scalars",
            "wrong_type_points",
            "wrong_count_one_array",
            "wrong_count_tuple_for_one",
        ):
            if is_known("failure:" + tool_id):
                continue
            with self.subTest(tool_id):
                self.assertEqual(toolerror_problems(tool_id), [])

    def test_a_result_json_cannot_carry_is_unserializable_result_never_text(self):
        worker = start()
        try:
            for kind in ("set", "object", "bytes", "complex"):
                with self.subTest(kind):
                    task = worker.task("unserialisable", {"kind": kind}).wait(30)
                    self.assertEqual((task.status, task.code), ("FAILED", "unserializable_result"))
                    self.assertIn("cannot be sent to the host", task.error)
                    self.assertTrue(worker.alive)
            self.assertEqual(worker.task("echo", {}).wait(30).status, "COMPLETE")
        finally:
            worker.close()

    def test_a_huge_result_arrives_whole(self):
        task, _ = run_tool("huge_output", {"megabytes": HUGE_MB}, timeout=180)
        self.assertEqual(task.status, "COMPLETE", task.error)
        values = task.outputs["results"][0]["values"]
        self.assertEqual(values["n"], HUGE_MB)
        self.assertEqual(len(values["text"]), HUGE_MB * 1_000_000)
        self.assertEqual(set(values["text"][:1000] + values["text"][-1000:]), {"x"})

    def test_every_whole_percent_arrives_as_itself(self):
        if is_known("lifecycle:progress_percent_is_rounded"):
            self.skipTest("known failure F19, watched by test_roundtrip_known_failures")
        self.assertEqual(progress_problems(), [])

    def test_many_progress_messages_all_arrive_and_the_task_still_ends(self):
        count = []
        worker = start()
        try:
            task = worker.task("many_progress", {"n": 20000}, on_update=lambda m, f: count.append(f)).wait(
                120
            )
            self.assertEqual(task.status, "COMPLETE")
            self.assertEqual(len(count), 20000)
            self.assertEqual(count, sorted(count), "progress never goes backwards")
            self.assertEqual((count[0], max(count)), (0.0, 0.99))
        finally:
            worker.close()


class Noise(unittest.TestCase):
    def test_nothing_a_tool_writes_to_stdout_reaches_the_protocol(self):
        for kind in ("print", "write", "raw_fd", "child", "flush_partial"):
            with self.subTest(kind):
                worker = start()
                try:
                    task = worker.task("noisy", {"kind": kind}).wait(30)
                    after = worker.task("echo", {"value": 5}).wait(30)
                finally:
                    worker.close()
                self.assertEqual(task.status, "COMPLETE", task.error)
                self.assertEqual(task.outputs["results"][0]["values"], {"kind": kind})
                self.assertEqual(
                    (after.status, after.outputs["results"][0]["values"]), ("COMPLETE", {"value": 5})
                )
                heard = "".join(worker.stderr)
                self.assertTrue(
                    "NOISE" in heard or "broken" in heard,
                    "the noise should be on stderr, where the log is: %r" % heard[-200:],
                )

    def test_a_stderr_flood_neither_blocks_the_tool_nor_grows_the_hosts_memory(self):
        worker = start()
        try:
            started = time.time()
            task = worker.task("flood_stderr", {"megabytes": FLOOD_MB}).wait(120)
            self.assertEqual(task.status, "COMPLETE", task.error)
            self.assertTrue(
                wait_for(lambda: "LAST LINE OF THE FLOOD" in "".join(list(worker.stderr)[-3:]), 30)
            )
            kept = sum(len(line) for line in worker.stderr)
            self.assertLessEqual(kept, client._Tail.LIMIT + 200, "the host keeps at most the last megabyte")
            self.assertGreater(worker.stderr.total, FLOOD_MB * 1_000_000 * 0.99)
            self.assertLess(time.time() - started, 100)
        finally:
            worker.close()

    def test_a_crash_message_carries_the_workers_last_words(self):
        worker = start()
        try:
            worker.task("noisy", {"kind": "print"}).wait(30)
            crashed = worker.task("crash_mid_task", {}).wait(30)
            self.assertEqual(crashed.status, "CRASHED")
            self.assertIn("NOISE", crashed.error)
            self.assertIn("--- worker output ---", crashed.error)
        finally:
            worker.close()


class HangsAndCancel(unittest.TestCase):
    def test_cooperative_cancel_ends_canceled_and_the_worker_is_reusable(self):
        worker = start()
        try:
            task = worker.task("hang", {"seconds": 120})
            task.launched.wait(30)
            task.cancel(grace=30)
            self.assertEqual(task.wait(30).status, "CANCELED")
            self.assertIsNone(task.error)
            self.assertTrue(worker.alive)
            self.assertEqual(worker.task("echo", {}).wait(30).status, "COMPLETE")
        finally:
            worker.close()

    def test_cancel_before_the_task_has_started_still_cancels_it(self):
        worker = start()
        try:
            for _ in range(25):
                task = worker.task("hang", {"seconds": 120})
                task.cancel(grace=30)  # no wait for LAUNCH: the request follows EXECUTE at once
                self.assertEqual(task.wait(30).status, "CANCELED")
            self.assertTrue(worker.alive)
        finally:
            worker.close()

    def test_a_cancel_for_a_finished_task_is_ignored(self):
        worker = start()
        try:
            task = worker.task("echo", {"value": 3}).wait(30)
            self.assertEqual(task.status, "COMPLETE")
            task.cancel(grace=None)
            self.assertEqual(
                worker.task("echo", {"value": 4}).wait(30).outputs["results"][0]["values"], {"value": 4}
            )
            self.assertEqual(task.status, "COMPLETE")
        finally:
            worker.close()

    def test_a_tool_that_ignores_cancel_is_stopped_with_its_children_and_says_so(self):
        with tempfile.TemporaryDirectory() as folder:
            pid_file = str(Path(folder) / "c.pid")
            worker = start()
            try:
                task = worker.task("deaf_hang", {"seconds": 300, "child_pid_file": pid_file})
                task.launched.wait(30)
                child = child_pid(pid_file)
                started = time.time()
                task.cancel(grace=1.0)
                task.wait(30)
                self.assertEqual(task.status, "CRASHED")
                self.assertIn("did not stop when Cancel was pressed", task.error)
                self.assertLess(time.time() - started, 20)
                self.assertTrue(
                    wait_for(lambda: not alive(child), 10), "the tool's child process is still running"
                )
                self.assertIsNotNone(worker.proc.poll())
            finally:
                worker.close()

    def test_a_cooperative_tool_cancelled_at_close_leaves_nothing_behind(self):
        with tempfile.TemporaryDirectory() as folder:
            pid_file = str(Path(folder) / "c.pid")
            worker = start()
            task = worker.task("hang", {"seconds": 300, "child_pid_file": pid_file})
            task.launched.wait(30)
            child = child_pid(pid_file)
            worker.close()
            self.assertTrue(
                wait_for(lambda: not alive(child), 10), "the tool's child process survived close()"
            )
            self.assertIsNotNone(worker.proc.poll())
            self.assertEqual(task.wait(10).status in ("CANCELED", "CRASHED"), True)

    def test_a_tool_that_leaves_a_child_after_it_returned_does_not_outlive_close(self):
        with tempfile.TemporaryDirectory() as folder:
            pid_file = str(Path(folder) / "c.pid")
            worker = start()
            task = worker.task("leave_child", {"child_pid_file": pid_file}).wait(30)
            self.assertEqual(task.status, "COMPLETE")
            child = child_pid(pid_file)
            self.assertTrue(alive(child))
            worker.close()
            self.assertTrue(wait_for(lambda: not alive(child), 10), "the child survived close()")

    @unittest.skipUnless(
        os.name == "posix", "the Windows worker ends its children with a job object (tests/windows)"
    )
    def test_children_die_when_the_host_goes_away(self):
        if is_known("lifecycle:children_die_when_the_host_goes_away"):
            self.skipTest("known failure F18, watched by test_roundtrip_known_failures")
        self.assertEqual(children_problems(), [])


class TimeoutThroughRunOnce(unittest.TestCase):
    """client.run_once with a timeout: the real entry point of the command line (needs the app registered)."""

    @classmethod
    def setUpClass(cls):
        env = {**os.environ, "PYTHONPATH": str(_paths.ROOT)}
        done = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "register", "--name", "failures", "--prefix", str(_paths.GENERIC_PREFIX),
             "--module", MODULE, "--pythonpath", str(APP_DIR), "--version", "0"],
            capture_output=True, text=True, env=env, encoding="utf-8",
        )  # fmt: skip
        assert done.returncode == 0, done.stderr

    def test_a_task_that_outlives_its_timeout_is_stopped_and_says_so(self):
        started = time.time()
        task = client.run_once("failures", "hang", {"seconds": 300}, timeout=2)
        self.assertEqual(task.status, "CRASHED")
        self.assertEqual(task.error, "timed out after 2 s")
        self.assertLess(time.time() - started, 30)
        self.assertIsNotNone(task.worker.proc.poll())

    def test_a_run_that_completes_returns_its_outputs_and_closes_the_worker(self):
        task = client.run_once("failures", "echo", {"value": 11}, timeout=60)
        self.assertEqual(task.status, "COMPLETE")
        self.assertEqual(task.outputs["results"][0]["values"], {"value": 11})
        self.assertIsNotNone(task.worker.proc.poll())

    def test_an_unwritable_results_folder_is_a_failure_with_a_message(self):
        with tempfile.TemporaryDirectory() as folder:
            blocker = Path(folder) / "i_am_a_file"
            blocker.write_text("x", encoding="utf-8")
            task = client.run_once("failures", "echo", {"value": 1, "_job_dir": str(blocker)}, timeout=60)
        self.assertEqual(task.status, "FAILED")
        self.assertTrue(task.error and task.error.strip())

    def test_an_unknown_app_is_a_start_error_with_the_installed_names(self):
        with self.assertRaises(client.WorkerStartError) as caught:
            client.run_once("no such app", "echo", {})
        self.assertIn("failures", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
