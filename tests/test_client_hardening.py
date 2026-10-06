"""Host client robustness: callbacks that raise, cancel that is ignored, finished tasks, shutdown, concurrent sends."""

import os
import tempfile
import threading
import time
import unittest
from unittest import mock

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import client, log, runs


def reset_logger():
    """The log file is chosen when the logger is first used: forget it so the next use follows LC_HOME."""
    import logging

    logger = logging.getLogger("labconstrictor")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    log._logger = None


class PrivateHome(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("LC_HOME")
        os.environ["LC_HOME"] = tempfile.mkdtemp(prefix="lchome_")
        reset_logger()

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("LC_HOME", None)
        else:
            os.environ["LC_HOME"] = self._saved
        reset_logger()


class ClientHardening(PrivateHome):
    def worker(self):
        return client.WorkerProcess(module="labconstrictor_tools.examples.synthetic")

    def test_a_progress_callback_that_raises_does_not_stop_the_task(self):
        def boom(message, fraction):
            raise ZeroDivisionError("callback bug")

        with self.worker() as w:
            task = w.task("slow", {"seconds": 0.6, "steps": 6}, on_update=boom).wait(30)
            self.assertEqual(task.status, "COMPLETE")
            self.assertEqual(
                w.task("scalar_echo", {}).wait(30).status, "COMPLETE"
            )  # the reader is still alive
        self.assertIn("progress callback failed", log.tail(50))
        self.assertIn("callback bug", log.tail(50))

    def test_cancel_escalates_to_a_kill_when_the_tool_ignores_it(self):
        with self.worker() as w:
            task = w.task("stubborn", {"seconds": 60})
            time.sleep(1.0)
            task.cancel(grace=0.5)
            task.wait(15)
            self.assertEqual(task.status, "CRASHED")
            self.assertIn("did not stop when Cancel was pressed", task.error)
        self.assertIn("ignored the cancel request", log.tail(50))

    def test_a_cooperative_cancel_does_not_kill_the_worker(self):
        with self.worker() as w:
            task = w.task("slow", {"seconds": 20, "steps": 40})
            time.sleep(1.0)
            task.cancel(grace=2.0)
            task.wait(10)
            self.assertEqual(task.status, "CANCELED")
            time.sleep(2.5)  # past the grace period: the timer must find the task done and do nothing
            self.assertTrue(w.alive)

    def test_finished_tasks_are_forgotten_by_the_worker(self):
        with self.worker() as w:
            for _ in range(3):
                self.assertEqual(w.task("scalar_echo", {}).wait(30).status, "COMPLETE")
            self.assertEqual(w.tasks, {})

    def test_close_that_has_to_kill_says_so(self):
        w = self.worker()
        w.task("stubborn", {"seconds": 60})
        time.sleep(1.0)
        w.close(timeout=0.2)
        self.assertFalse(w.alive)
        self.assertIn("did not exit within", log.tail(50))

    def test_a_failed_initialisation_does_not_leave_the_process_running(self):
        started = []
        real_popen = client.subprocess.Popen

        def spy(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            started.append(proc)
            return proc

        with (
            mock.patch.object(client.subprocess, "Popen", side_effect=spy),
            mock.patch.object(
                client.threading.Thread, "start", side_effect=RuntimeError("cannot start new thread")
            ),
            self.assertRaises(RuntimeError),
        ):
            self.worker()
        self.assertEqual(len(started), 1)
        self.assertIsNotNone(started[0].poll())  # already stopped, not orphaned

    def test_requests_from_several_threads_are_written_one_at_a_time(self):
        class Slow:
            busy, overlaps, lines = False, 0, []

            def write(self, text):
                if self.busy:
                    self.overlaps += 1
                self.busy = True
                time.sleep(0.002)
                self.lines.append(text)
                self.busy = False

            def flush(self):
                pass

        worker = client.WorkerProcess.__new__(client.WorkerProcess)
        worker._send_lock = threading.Lock()
        worker.proc = mock.Mock(stdin=Slow())
        threads = [
            threading.Thread(target=lambda: [worker._send({"n": i}) for i in range(20)]) for _ in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(worker.proc.stdin.overlaps, 0)
        self.assertEqual(len(Slow.lines), 80)


class RunRecordPruning(PrivateHome):
    def test_a_folder_that_cannot_be_removed_is_logged_and_the_others_still_go(self):
        folder = runs.runs_dir()
        folder.mkdir(parents=True)
        for name in ("a", "b", "c", "d"):
            (folder / name).mkdir()
        real = runs.shutil.rmtree

        def picky(path, *args, **kwargs):
            if path.name == "a":
                raise PermissionError("held open")
            return real(path, *args, **kwargs)

        with mock.patch.object(runs.shutil, "rmtree", side_effect=picky):
            runs._prune(keep=1)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["a", "d"])
        self.assertIn("could not remove the old run record", log.tail(20))


class StderrTail(unittest.TestCase):
    def test_total_counts_everything_ever_received_even_after_trimming(self):
        tail = client._Tail()
        tail.append("a" * 10)
        mark = tail.total
        for _ in range(3):
            tail.append("b" * (client._Tail.LIMIT // 2))  # forces the bounded tail to drop old lines
        self.assertEqual(mark, 10)
        self.assertEqual(tail.total - mark, 3 * (client._Tail.LIMIT // 2))
        self.assertLessEqual(len("".join(tail)), client._Tail.LIMIT + client._Tail.LIMIT // 2)


if __name__ == "__main__":
    unittest.main()
