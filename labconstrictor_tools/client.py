"""Minimal Python host client for the worker (Appose protocol subset). Used by Napari and the tests.

with WorkerProcess("myapp") as worker:
    task = worker.task("tool_id", {"param": 1}, on_update=lambda message, fraction: ...)
    task.wait()
    task.status    # COMPLETE | FAILED | CANCELED | CRASHED
"""

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from . import log, registry

_SCRUBBED_ENV = ("PYTHONHOME", "VIRTUAL_ENV", "CONDA_PREFIX", "QT_PLUGIN_PATH", "PYTHONPATH")
_STATUS_BY_RESPONSE = {
    "COMPLETION": "COMPLETE",
    "CANCELATION": "CANCELED",
    "FAILURE": "FAILED",
    "CRASH": "CRASHED",
}


def _brief(inputs, limit=300):
    """Inputs for the log: paths and scalars as they are, bulky shared-memory descriptors shortened."""
    text = json.dumps(inputs, default=str)
    return text if len(text) <= limit else text[:limit] + "...(%d chars)" % len(text)


class WorkerStartError(RuntimeError):
    """The worker process could not even be started; the message says what to check."""


class WorkerProcess:
    """One worker subprocess running in the app's own interpreter. Reusable for several tasks."""

    def __init__(self, app=None, *, module=None, pythonpath=(), python=None):
        """`app`: a registered app. Without it, start `module` directly (authors testing before registering)."""
        if app is not None:
            self.entry = registry.load_all()[app]
        else:
            self.entry = {
                "python": python or sys.executable,
                "module": module,
                "pythonpath": [str(Path(p).resolve()) for p in pythonpath],
                "runtime_path": registry.runtime_path(),
            }
        env = {key: value for key, value in os.environ.items() if key not in _SCRUBBED_ENV}
        env.update(
            PYTHONPATH=os.pathsep.join([self.entry["runtime_path"], *self.entry["pythonpath"]]),
            PYTHONNOUSERSITE="1",
            PYTHONIOENCODING="utf-8",
            PYTHONUNBUFFERED="1",
        )
        command = [
            self.entry["python"],
            "-m",
            "labconstrictor_tools",
            "serve",
            "--module",
            self.entry["module"],
        ]
        try:
            self.proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # no console flash on Windows
            )
        except OSError as error:
            reason = log.explain_spawn_error(error, command)
            log.error("worker start failed: %s | command=%s", reason, command)
            raise WorkerStartError(reason + " (details in %s)" % log.log_path()) from error
        self._command, self._started = command, time.time()
        log.info(
            "worker started pid=%s app=%s python=%s module=%s PYTHONPATH=%s",
            self.proc.pid,
            app or "(direct)",
            command[0],
            self.entry["module"],
            env["PYTHONPATH"],
        )
        self.tasks = {}
        self.stderr = []
        threading.Thread(target=self._read_responses, daemon=True).start()
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_thread.start()

    @property
    def alive(self):
        return self.proc.poll() is None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def task(self, tool_id, inputs, on_update=None):
        task = Task(self, tool_id, on_update)
        self.tasks[task.id] = task
        log.info(
            "task %s start tool=%s worker=%s inputs=%s", task.id[:8], tool_id, self.proc.pid, _brief(inputs)
        )
        self._send({"task": task.id, "requestType": "EXECUTE", "script": "lc:" + tool_id, "inputs": inputs})
        return task

    def close(self, timeout=5):
        """Ask the worker to exit (close stdin); kill it if it does not."""
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=timeout)
        except Exception:  # noqa: BLE001 - best effort shutdown
            self.kill()

    def kill(self):
        self.proc.kill()
        self.proc.wait()

    def _send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def _read_responses(self):
        for line in self.proc.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            task = self.tasks.get(message.get("task"))
            if task:
                task.handle(message)
        self._on_exit()

    def _on_exit(self):
        """stdout closed: the worker is gone. Unfinished tasks crashed - say why, with the worker's own last words."""
        returncode = self.proc.wait()
        self._stderr_thread.join(2)
        tail = "".join(self.stderr)[-2500:].strip()
        pending = [t for t in self.tasks.values() if not t.done.is_set()]
        log.info(
            "worker pid=%s exited code=%s after %.1fs", self.proc.pid, returncode, time.time() - self._started
        )
        if pending:
            hint = log.hint_for_exit(returncode, tail)
            message = "worker exited unexpectedly (code %s)" % returncode
            if hint:
                message += ": " + hint
            if tail:
                message += "\n--- worker output ---\n" + tail
            log.error("%s", message.replace("\n", " | "))
        else:
            message = "worker exited"
        for task in pending:
            task.handle({"responseType": "CRASH", "error": message})

    def _read_stderr(self):
        for line in self.proc.stderr:
            self.stderr.append(line)
            log.logger().debug("worker[%s] %s", self.proc.pid, line.rstrip())


class Task:
    def __init__(self, worker, tool_id, on_update):
        self.worker, self.tool_id, self.on_update = worker, tool_id, on_update
        self.id = str(uuid.uuid4())
        self.done = threading.Event()
        self.launched = threading.Event()  # the worker accepted the task (its LAUNCH message arrived)
        self.status = "RUNNING"
        self.outputs, self.error, self.code, self.traceback = {}, None, None, None

    def handle(self, message):
        if self.done.is_set():  # a finished task never changes state (e.g. when the worker later exits)
            return
        kind = message["responseType"]
        if kind == "LAUNCH":
            self.launched.set()
        if kind == "UPDATE" and self.on_update:
            fraction = message["current"] / message["maximum"] if message.get("maximum") else None
            self.on_update(message.get("message"), fraction)
        elif kind in _STATUS_BY_RESPONSE:
            self.status = _STATUS_BY_RESPONSE[kind]
            self.outputs = message.get("outputs", {})
            self.error, self.code = message.get("error"), message.get("code")
            self.traceback = message.get("traceback")
            self._log_outcome()
            self.done.set()

    def _log_outcome(self):
        if self.status == "COMPLETE":
            log.info(
                "task %s COMPLETE tool=%s timings=%s", self.id[:8], self.tool_id, self.outputs.get("timings")
            )
        elif self.status == "CANCELED":
            log.info("task %s CANCELED tool=%s", self.id[:8], self.tool_id)
        else:
            log.error(
                "task %s %s tool=%s code=%s error=%s%s",
                self.id[:8],
                self.status,
                self.tool_id,
                self.code,
                (self.error or "").replace("\n", " | "),
                ("\n" + self.traceback) if self.traceback else "",
            )

    def cancel(self):
        """Request cooperative cancellation (the tool must call check_cancel()); kill the worker if it ignores it."""
        self.worker._send({"task": self.id, "requestType": "CANCEL"})

    def wait(self, timeout=None):
        """Block until finished or `timeout` seconds passed (then status stays RUNNING). Returns self."""
        self.done.wait(timeout)
        return self


def run_once(app, tool_id, inputs, on_update=None, timeout=None, record=False):
    """Fresh worker for one run. If `timeout` seconds pass the worker is killed and the task is CRASHED.
    With record=True a run record is written (see runs.py); it is available as `task.record_dir`."""
    started = time.time()
    with WorkerProcess(app) as worker:
        task = worker.task(tool_id, inputs, on_update).wait(timeout)
        if not task.done.is_set():
            worker.kill()
            task.wait(5)
            task.error = "timed out after %s s" % timeout
            log.error("task %s timed out after %s s, worker killed", task.id[:8], timeout)
        if record:
            from . import runs

            task.record_dir = runs.record(
                app, tool_id, inputs, task, time.time() - started, "".join(worker.stderr)
            )
        return task
