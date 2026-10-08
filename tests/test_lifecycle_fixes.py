"""Worker and client lifecycle: guards for the fixes of F13, F17, F18, F19 and F21 that the matrix does not already cover
(docs/REGRESSION_LEDGER.md names the main guard of each; these test the edges)."""

import logging
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from multiprocessing import shared_memory
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401  (must come first)
from test_roundtrip_failures import alive, child_pid, start, wait_for

from labconstrictor_tools import registry, worker
from labconstrictor_tools.client import WorkerProcess

SUBPROCESS_TIMEOUT_S = 60
EXIT_AFTER_ATTACH = (
    "import sys; sys.path.insert(0, %r)\n"
    "from labconstrictor_tools import convert\n"
    "shm = convert._attach_shared_memory(sys.argv[1])\n"
    "print(bytes(shm.buf[:3]).hex())\n"
    "shm.close()\n"
)


class SharedMemoryAttach(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX shared memory is named, and tracked per process")
    def test_a_process_that_only_attached_leaves_the_block_and_its_stderr_alone(self):
        block = shared_memory.SharedMemory(create=True, size=8)
        try:
            block.buf[:3] = bytes([1, 2, 3])
            done = subprocess.run(
                [sys.executable, "-c", EXIT_AFTER_ATTACH % str(_paths.ROOT), block.name],
                capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_S, encoding="utf-8",
            )  # fmt: skip
            self.assertEqual((done.returncode, done.stdout.strip()), (0, "010203"), done.stderr)
            self.assertEqual(done.stderr, "", "the attaching process must not complain about leaked blocks")
            again = shared_memory.SharedMemory(
                name=block.name
            )  # raises FileNotFoundError when it was unlinked
            again.close()
        finally:
            block.close()
            block.unlink()  # the host-side owner still cleans up its own block


class DeadWorker(unittest.TestCase):
    def test_a_task_on_a_crashed_worker_is_crashed_with_the_exit_code_and_is_not_kept(self):
        worker_ = start()
        try:
            worker_.task("crash_mid_task", {"how": "exit"}).wait(30)
            worker_.proc.wait(30)
            task = worker_.task("echo", {})
            self.assertTrue(task.done.is_set())
            self.assertEqual(task.status, "CRASHED")
            self.assertIn("code 7", task.error)
            self.assertNotIn(task.id, worker_.tasks)
            self.assertEqual(worker_.tasks, {})
        finally:
            worker_.close()

    def test_a_task_on_a_worker_the_host_already_closed_is_crashed_too(self):
        worker_ = start()
        worker_.close()
        task = worker_.task("echo", {})
        self.assertEqual(task.status, "CRASHED")
        self.assertTrue(task.error)
        self.assertEqual(worker_.tasks, {})


class ProcessGroup(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "process groups")
    def test_a_worker_started_without_its_own_group_still_ends_what_its_tool_started(self):
        """The Java hosts (Fiji's Appose Service, QuPath's ProcessBuilder) cannot start a process in a new session: the worker
        puts itself in one, so the children of its tool die with it all the same."""

        def spawn_like_a_java_host(command, env):
            return subprocess.Popen(  # same pipes as the client, but NO start_new_session
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding="utf-8", env=env,
            )  # fmt: skip

        with (
            tempfile.TemporaryDirectory() as folder,
            mock.patch.object(WorkerProcess, "_spawn", staticmethod(spawn_like_a_java_host)),
        ):
            pid_file = str(Path(folder) / "c.pid")
            worker_ = start()
            try:
                self.assertEqual(
                    os.getpgid(worker_.proc.pid), os.getpgid(0), "the test needs a worker in our group"
                )
                task = worker_.task("hang", {"child_pid_file": pid_file})
                task.launched.wait(30)
                child = child_pid(pid_file)
                self.assertEqual(
                    os.getpgid(worker_.proc.pid), worker_.proc.pid, "the worker leads its own group now"
                )
                worker_.proc.stdin.close()
                worker_.proc.wait(30)
                self.assertTrue(
                    wait_for(lambda: not alive(child), 5.0), "the tool's child survived the worker"
                )
            finally:
                worker_.kill()


class GroupListingFails(unittest.TestCase):
    """The one place a stand-in is right: `ps` cannot be made to fail on demand, and the real killpg would end the test run."""

    @unittest.skipUnless(os.name == "posix", "process groups")
    def test_when_the_members_cannot_be_listed_the_whole_group_is_ended_and_the_reason_logged(self):
        me = os.getpid()
        with (
            mock.patch.object(os, "getpgrp", return_value=me),
            mock.patch.object(worker.Worker, "_group_members", side_effect=FileNotFoundError("ps")),
            mock.patch.object(os, "killpg") as killpg,
            self.assertLogs("labconstrictor", logging.WARNING) as logged,
        ):
            worker.Worker._end_process_group()
        killpg.assert_called_once_with(me, signal.SIGKILL)
        self.assertIn("cannot list its process group", logged.output[0])

    @unittest.skipUnless(os.name == "posix", "process groups")
    def test_the_members_listing_finds_this_process_in_its_own_group(self):
        self.assertIn(os.getpid(), worker.Worker._group_members(os.getpgrp()))


class Progress(unittest.TestCase):
    def test_every_whole_percent_and_the_documented_ties(self):
        for k in range(101):
            self.assertEqual(worker._whole_percent(k / 100), k, k)
        self.assertEqual(worker._whole_percent(0.294), 29)
        self.assertEqual(worker._whole_percent(0.296), 30)
        self.assertEqual(worker._whole_percent(0.5), 50)
        self.assertEqual(worker._whole_percent(0.125 / 5), 3, "a tie (2.5 %) rounds up")
        self.assertEqual(worker._whole_percent(0.0), 0)
        self.assertEqual(worker._whole_percent(1.0), 100)


class ReplaceRetry(unittest.TestCase):
    """The one place for a mock of an OS call: it tests OUR retry logic (Windows refusals cannot be produced on demand)."""

    def refused(self):
        return PermissionError(5, "Access is denied")

    def test_a_refusal_is_retried_logged_and_the_file_ends_up_written(self):
        calls = []

        def replace(source, target):
            calls.append(1)
            if len(calls) < 3:
                raise self.refused()

        with (
            mock.patch.object(registry, "_is_windows", return_value=True),
            mock.patch.object(registry.os, "replace", side_effect=replace),
            mock.patch.object(registry.time, "sleep") as sleep,
        ):
            with self.assertLogs("labconstrictor", logging.WARNING) as logged:
                registry._replace(Path("a.tmp"), Path("a.json"))
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_called_with(registry.REPLACE_PAUSE_S)
        self.assertEqual(len(logged.records), 2, "each retry is logged")
        self.assertIn("attempt 1 of %d" % registry.REPLACE_ATTEMPTS, logged.output[0])

    def test_a_refusal_that_never_ends_is_raised_with_the_reason_and_what_to_do(self):
        with (
            mock.patch.object(registry, "_is_windows", return_value=True),
            mock.patch.object(registry.os, "replace", side_effect=self.refused()) as replace,
            mock.patch.object(registry.time, "sleep"),
        ):
            with self.assertLogs("labconstrictor", logging.WARNING):
                with self.assertRaises(PermissionError) as caught:
                    registry._replace(Path("a.tmp"), Path("a.json"))
        self.assertEqual(replace.call_count, registry.REPLACE_ATTEMPTS)
        text = str(caught.exception)
        self.assertIn("a.json", text)
        self.assertIn("antivirus", text)
        self.assertIn("run the command again", text)

    def test_a_refusal_is_not_retried_off_windows(self):
        with (
            mock.patch.object(registry, "_is_windows", return_value=False),
            mock.patch.object(registry.os, "replace", side_effect=self.refused()) as replace,
            mock.patch.object(registry.time, "sleep") as sleep,
        ):
            with self.assertRaises(PermissionError):
                registry._replace(Path("a.tmp"), Path("a.json"))
        self.assertEqual((replace.call_count, sleep.call_count), (1, 0))

    def test_write_atomic_goes_through_the_retry_and_leaves_no_temporary_file(self):
        import tempfile

        real = os.replace
        seen = []

        def flaky(source, target):
            seen.append(1)
            if len(seen) == 1:
                raise self.refused()
            real(source, target)

        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "x.json"
            with (
                mock.patch.object(registry, "_is_windows", return_value=True),
                mock.patch.object(registry.os, "replace", side_effect=flaky),
                mock.patch.object(registry.time, "sleep"),
                self.assertLogs("labconstrictor", logging.WARNING),
            ):
                registry._write_atomic(target, "hello")
            self.assertEqual(target.read_text(encoding="utf-8"), "hello")
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["x.json"])


if __name__ == "__main__":
    unittest.main()
