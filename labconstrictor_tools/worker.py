"""LabConstrictor tool worker: runs INSIDE an app's own interpreter and speaks the Appose worker protocol.

Unlike `appose.python_worker`, it never executes host-supplied code: an EXECUTE `script` must be
`lc:<tool_id>` naming a tool declared by the module given on the command line.
"""

import importlib
import importlib.util
import os
import queue
import shutil
import sys
import tempfile
import threading
import time
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import convert, runtime
from . import types as T
from .decorators import tools_in
from .introspection import describe_tool
from .protocol import JOB_DIR_KEY, Channel, tool_id_from_script

ORPHAN_GRACE_S = 10.0  # after the host disappears, how long a running tool gets to notice and stop


class Worker:
    def __init__(self, module: str, pythonpath: Sequence[str] = ()) -> None:
        for path in pythonpath:
            sys.path.insert(0, path)
        self.channel = Channel()
        self._preload_numpy()
        try:
            importlib.import_module(module)
        except (
            BaseException
        ):  # noqa: BLE001 - report everything an author needs, then exit with a recognisable code
            print(
                "LabConstrictor worker context:\n  python:    %s (%s)\n  cwd:       %s\n  sys.path:  %s\n%s"
                "LabConstrictor worker: cannot import tool module %r (details above)"
                % (
                    sys.executable,
                    sys.version.split()[0],
                    os.getcwd(),
                    sys.path,
                    traceback.format_exc(),
                    module,
                ),
                file=sys.stderr,
                flush=True,
            )
            raise SystemExit(3) from None
        self.tools = {tool.id: tool for tool in tools_in(module)}
        self.schemas = {tid: describe_tool(tool) for tid, tool in self.tools.items()}
        self._cancel_events: dict[str, threading.Event] = {}
        self._owned_dirs: set[Path] = set()  # job folders this worker created and has not handed over yet

    @staticmethod
    def _preload_numpy():
        # Windows: first importing numpy/scipy on a non-main thread while the main thread blocks on stdin can
        # deadlock (numpy issue 24290). Importing numpy here, and running tools on the main thread, avoids it.
        if importlib.util.find_spec("numpy") is not None:
            import numpy  # noqa: F401

    # ---- serving ------------------------------------------------------
    def serve(self) -> None:
        """Run tasks on the MAIN thread; a helper thread reads stdin so CANCEL is seen while a tool runs."""
        pending: queue.Queue[tuple[str, str, Any] | None] = queue.Queue()
        threading.Thread(target=self._read_requests, args=(pending,), daemon=True).start()
        while True:
            item = pending.get()
            if item is None:  # stdin closed: exit once the current task has stopped
                return
            self._run_task(*item)

    @staticmethod
    def _complain(text, *args):
        print("LabConstrictor worker: " + text % args, file=sys.stderr, flush=True)

    def _read_requests(self, pending):
        try:
            for request in self.channel.read_requests():
                self._dispatch(request, pending)
        except (
            BaseException
        ):  # noqa: BLE001 - the reader must never die silently: the main thread would wait for ever
            self._complain("the request reader failed, shutting down:\n%s", traceback.format_exc())
        # stdin closed: with a task still running the host is gone (crash, kill) - nobody is listening any more.
        for event in list(self._cancel_events.values()):
            event.set()
        if self._cancel_events:
            timer = threading.Timer(ORPHAN_GRACE_S, self._orphan_exit)
            timer.daemon = True
            timer.start()
        pending.put(None)

    def _dispatch(self, request, pending):
        task, kind = request.get("task"), request.get("requestType")
        if not isinstance(task, str) or not task:
            self._complain("ignoring a %r request without a text task id", kind)
        elif kind == "EXECUTE":
            script, inputs = request.get("script"), request.get("inputs")
            if (
                task in self._cancel_events
            ):  # an answer would end the running task of that id on the host: stay silent
                self._complain("ignoring EXECUTE for task %r: that task id is still in use", task)
            elif not isinstance(script, str) or not (inputs is None or isinstance(inputs, dict)):
                self._complain(
                    "rejecting EXECUTE for task %r: script must be text and inputs an object", task
                )
                self.channel.send(
                    task,
                    "FAILURE",
                    error="[bad_request] EXECUTE needs a text script and an object of inputs",
                    code="bad_request",
                )
            else:
                self._cancel_events[task] = threading.Event()
                self.channel.send(task, "LAUNCH")
                pending.put((task, script, inputs or {}))
        elif kind == "CANCEL":
            event = self._cancel_events.get(task)
            if event is None:
                self._complain(
                    "CANCEL for task %r, which is not running (already finished or never started)", task
                )
            else:
                event.set()
        else:
            self._complain("ignoring a request of unknown type %r for task %r", kind, task)

    def _orphan_exit(self):
        """The host is gone and the tool ignored the cancel request: leave, but not without removing our temp folders."""
        for path in list(self._owned_dirs):
            shutil.rmtree(path, ignore_errors=True)
        os._exit(1)

    def _remove_job_dir(self, path):
        shutil.rmtree(path, ignore_errors=True)
        if path.exists():
            self._complain("could not remove the temporary folder %s completely", path)

    # ---- one task -----------------------------------------------------
    def _run_task(self, task, script, inputs):
        cancel = self._cancel_events[task]
        runtime.install(
            cancelled=cancel.is_set,
            progress=lambda fraction, message: self._send_progress(task, fraction, message),
        )
        job_dir, owns_job_dir = None, False
        try:
            if cancel.is_set():  # cancelled before it even started (e.g. the host went away)
                raise T.Cancelled()
            tool_id = tool_id_from_script(script)
            if tool_id not in self.tools:
                raise T.ToolError("unknown_tool", "only declared tools may be executed; got %r" % script[:40])
            inputs = dict(inputs)
            given = inputs.pop(JOB_DIR_KEY, None)
            owns_job_dir = given is None
            job_dir = Path(given or tempfile.mkdtemp(prefix="lcjob_"))
            job_dir.mkdir(parents=True, exist_ok=True)
            if owns_job_dir:
                self._owned_dirs.add(job_dir)
            final = self._execute(tool_id, inputs, job_dir, cancel)
        except T.Cancelled:
            final = ("CANCELATION", {})
        except T.ToolError as error:
            final = ("FAILURE", {"error": "[%s] %s" % (error.code, error.message), "code": error.code})
        except (
            SystemExit,
            KeyboardInterrupt,
        ) as error:  # a tool leaving the interpreter must still get an answer
            final = self._tool_exit_outcome(script, error)
        except Exception as error:  # noqa: BLE001 - any tool failure becomes a structured FAILURE
            final = self._tool_crash_outcome(script, error)
        finally:
            runtime.install()  # late progress()/cancelled() calls from a tool's leftover threads do nothing
        if job_dir is not None and owns_job_dir and final[0] != "COMPLETION":
            # Clean up BEFORE the terminal message: a client that sees CANCELED/FAILED may look at the temp dir at once.
            self._remove_job_dir(job_dir)
        self._owned_dirs.discard(job_dir)  # a finished result belongs to the host now
        self._cancel_events.pop(task, None)
        self.channel.send(task, final[0], **final[1])

    def _tool_exit_outcome(self, script, error):
        """A tool called sys.exit() or was interrupted: complain on stderr, answer with a FAILURE."""
        self._complain(
            "tool %r tried to stop the worker with %s(%r)", script, type(error).__name__, error.args
        )
        return (
            "FAILURE",
            {
                "error": "[%s] the tool called sys.exit() or was interrupted (%r)"
                % (type(error).__name__, error.args),
                "code": type(error).__name__,
            },
        )

    @staticmethod
    def _tool_crash_outcome(script, error):
        """An unexpected exception in a tool (call from its `except` block): traceback to stderr and into the FAILURE."""
        print(
            "LabConstrictor worker: tool %r failed:\n%s" % (script, traceback.format_exc()),
            file=sys.stderr,
            flush=True,
        )
        return (
            "FAILURE",
            {
                "error": "[%s] %s" % (type(error).__name__, error),
                "code": type(error).__name__,
                "traceback": traceback.format_exc(),
            },
        )

    def _execute(self, tool_id, inputs, job_dir, cancel):
        schema = self.schemas[tool_id]
        t0 = time.perf_counter()
        kwargs = convert.load_inputs(schema, inputs, self.tools[tool_id].fn)
        t1 = time.perf_counter()
        returned = self.tools[tool_id].fn(**kwargs)
        t2 = time.perf_counter()
        if cancel.is_set():
            raise T.Cancelled()
        results = convert.build_results(schema, returned, job_dir)
        t3 = time.perf_counter()
        outputs = {
            "results": results,
            "job_dir": str(job_dir),
            "timings": {
                "load_inputs_s": round(t1 - t0, 4),
                "tool_s": round(t2 - t1, 4),
                "write_results_s": round(t3 - t2, 4),
            },
            "diagnostics": {
                "sys.executable": sys.executable,
                "sys.prefix": sys.prefix,
                "python": sys.version.split()[0],
                "pid": os.getpid(),
            },
        }
        return ("COMPLETION", {"outputs": outputs})

    def _send_progress(self, task, fraction, message):
        if task not in self._cancel_events:
            return  # the task is over
        fields = {"message": str(message)}
        if fraction is not None:
            fields.update(current=int(100 * fraction), maximum=100)
        self.channel.send(task, "UPDATE", **fields)
