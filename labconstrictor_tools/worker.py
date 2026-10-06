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

    def _read_requests(self, pending):
        for request in self.channel.read_requests():
            task, kind = request.get("task"), request.get("requestType")
            if kind == "EXECUTE":
                self._cancel_events[task] = threading.Event()
                self.channel.send(task, "LAUNCH")
                pending.put((task, request.get("script", ""), request.get("inputs")))
            elif kind == "CANCEL" and task in self._cancel_events:
                self._cancel_events[task].set()
        # stdin closed: with a task still running the host is gone (crash, kill) - nobody is listening any more.
        for event in list(self._cancel_events.values()):
            event.set()
        if self._cancel_events:
            timer = threading.Timer(ORPHAN_GRACE_S, os._exit, args=(1,))
            timer.daemon = True
            timer.start()
        pending.put(None)

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
            inputs = dict(inputs or {})
            given = inputs.pop(JOB_DIR_KEY, None)
            owns_job_dir = given is None
            job_dir = Path(given or tempfile.mkdtemp(prefix="lcjob_"))
            job_dir.mkdir(parents=True, exist_ok=True)
            final = self._execute(tool_id, inputs, job_dir, cancel)
        except T.Cancelled:
            final = ("CANCELATION", {})
        except T.ToolError as error:
            final = ("FAILURE", {"error": "[%s] %s" % (error.code, error.message), "code": error.code})
        except Exception as error:  # noqa: BLE001 - any tool failure becomes a structured FAILURE
            print(
                "LabConstrictor worker: tool %r failed:\n%s" % (script, traceback.format_exc()),
                file=sys.stderr,
                flush=True,
            )
            final = (
                "FAILURE",
                {
                    "error": "[%s] %s" % (type(error).__name__, error),
                    "code": type(error).__name__,
                    "traceback": traceback.format_exc(),
                },
            )
        finally:
            self._cancel_events.pop(task, None)
        if job_dir is not None and owns_job_dir and final[0] != "COMPLETION":
            # Clean up BEFORE the terminal message: a client that sees CANCELED/FAILED may look at the temp dir at once.
            shutil.rmtree(job_dir, ignore_errors=True)
        self.channel.send(task, final[0], **final[1])

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
        fields = {"message": str(message)}
        if fraction is not None:
            fields.update(current=int(100 * fraction), maximum=100)
        self.channel.send(task, "UPDATE", **fields)
