"""LabConstrictor tool worker: runs INSIDE an app's own interpreter and speaks the Appose worker protocol.

Unlike `appose.python_worker`, it never executes host-supplied code: an EXECUTE `script` must be
`lc:<tool_id>` naming a tool declared by the module given on the command line.
"""

import importlib
import importlib.util
import math
import os
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import _winjob, convert, log, runtime
from . import types as T
from .decorators import tools_in
from .introspection import describe_tool
from .protocol import JOB_DIR_KEY, Channel, tool_id_from_script

# a task's end as the host hears it: (terminal response type, its fields)
Outcome = tuple[str, dict[str, Any]]

SCRIPT_PREVIEW_CHARS = 40  # how much of a refused script is echoed back in the error
PROGRESS_MAXIMUM = 100  # progress is reported to hosts as current/maximum on this scale
PROGRESS_HALF = 0.5  # added before flooring: a tie rounds up
PS_TIMEOUT_S = 10  # listing the worker's process group at exit
ORPHAN_GRACE_S = 10.0  # after the host disappears, how long a running tool gets to notice and stop


def _whole_percent(fraction: float) -> int:
    """The whole percent nearest to `fraction` (0..1), a tie going up: 0.295 -> 30 (a plain int() lost a percent whenever
    100 * fraction fell just below the integer: 0.29 was shown as 28 %). Every host that rounds a fraction itself must
    do the same (Java's Math.round is half-up already)."""
    return math.floor(PROGRESS_MAXIMUM * fraction + PROGRESS_HALF)


class Worker:
    """Serves tool calls from one module: a reader thread takes requests so CANCEL arrives while the main thread runs a tool."""

    def __init__(self, module: str, pythonpath: Sequence[str] = ()) -> None:
        for path in pythonpath:
            sys.path.insert(0, path)
        self.channel = Channel()
        _winjob.kill_children_with_me()  # Windows: processes a tool starts end with the worker
        self._lead_own_process_group()  # POSIX: the same, whoever started us (see _end_process_group)
        self._preload_numpy()
        try:
            importlib.import_module(module)
        # report everything an author needs, then exit with a recognisable code
        except BaseException:  # noqa: BLE001 - see above
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
            raise SystemExit(log.EXIT_TOOL_IMPORT_FAILED) from None
        self.tools = {tool.id: tool for tool in tools_in(module)}
        self.schemas = {tid: describe_tool(tool) for tid, tool in self.tools.items()}
        self._cancel_events: dict[str, threading.Event] = {}
        self._owned_dirs: set[Path] = set()  # job folders this worker created and has not handed over yet

    @staticmethod
    def _preload_numpy() -> None:
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
                self._end_process_group()
                return
            self._run_task(*item)

    @staticmethod
    def _complain(text: str, *args: object) -> None:
        print("LabConstrictor worker: " + text % args, file=sys.stderr, flush=True)

    def _read_requests(self, pending: queue.Queue[tuple[str, str, Any] | None]) -> None:
        try:
            for request in self.channel.read_requests():
                self._dispatch(request, pending)
        # the reader must never die silently: the main thread would wait for ever
        except BaseException:  # noqa: BLE001 - see above
            self._complain("the request reader failed, shutting down:\n%s", traceback.format_exc())
        # stdin closed: with a task still running the host is gone (crash, kill) - nobody is listening any more.
        for event in list(self._cancel_events.values()):
            event.set()
        if self._cancel_events:
            timer = threading.Timer(ORPHAN_GRACE_S, self._orphan_exit)
            timer.daemon = True
            timer.start()
        pending.put(None)

    def _dispatch(self, request: dict[str, Any], pending: queue.Queue[tuple[str, str, Any] | None]) -> None:
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

    def _orphan_exit(self) -> None:
        """The host is gone and the tool ignored the cancel request: leave, but not without removing our temp folders."""
        for path in list(self._owned_dirs):
            shutil.rmtree(path, ignore_errors=True)
        self._end_process_group()
        os._exit(1)

    @staticmethod
    def _lead_own_process_group() -> None:
        """POSIX: become the leader of a process group of our own, so that _end_process_group can end everything a tool starts.

        The Python client starts the worker that way (start_new_session), but the Java hosts (Fiji's Appose Service, QuPath's
        ProcessBuilder) cannot, so the worker does it itself: no host has to do anything. setsid() fails only for a process that
        already leads a group, which is the case we skip.
        """
        if os.name == "posix" and os.getpgrp() != os.getpid():
            os.setsid()

    @staticmethod
    def _end_process_group() -> None:
        """POSIX: the host is gone, so nothing a tool started may outlive the worker (Windows: the job object of _winjob).

        The worker leads a process group of its own (the client asks for one, and `_lead_own_process_group` makes it so for
        every other host), and the subprocesses of a tool inherit it. Every other member is sent SIGKILL and the worker then
        leaves normally (exit status 0, coverage and logs written). Only when the members cannot be listed does the worker kill
        the whole group including itself, after flushing its output: leaving a process behind is the worse outcome.
        """
        if (
            os.name != "posix" or os.getpgrp() != os.getpid()
        ):  # a safety net: never signal a group that is not ours
            return
        me = os.getpid()
        try:
            members = Worker._group_members(me)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            log.warning(
                "worker: cannot list its process group (%s: %s); ending the whole group",
                type(error).__name__,
                error,
            )
            for stream in (sys.stdout, sys.stderr):
                try:
                    stream.flush()
                except (
                    OSError,
                    ValueError,
                ) as flush_error:  # the pipe is already closed: nobody is listening
                    log.logger().debug(
                        "worker: flushing failed (%s: %s)", type(flush_error).__name__, flush_error
                    )
            os.killpg(me, signal.SIGKILL)
            return
        for pid in members:
            if pid != me:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # it ended on its own just now: what we wanted

    @staticmethod
    def _group_members(group: int) -> list[int]:
        """The pids of every process in process group `group` (`ps` exists on Linux and macOS alike)."""
        listing = subprocess.run(
            ["ps", "-A", "-o", "pid=,pgid="],  # noqa: S607 - ps is found on PATH by design
            capture_output=True, text=True, timeout=PS_TIMEOUT_S, check=True,
        )  # fmt: skip
        pairs = (line.split() for line in listing.stdout.splitlines() if line.strip())
        return [int(pid) for pid, pgid in pairs if int(pgid) == group]

    def _remove_job_dir(self, path: Path) -> None:
        shutil.rmtree(path, ignore_errors=True)
        if path.exists():
            self._complain("could not remove the temporary folder %s completely", path)

    # ---- one task -----------------------------------------------------
    def _run_task(self, task: str, script: str, inputs: dict[str, Any]) -> None:
        cancel = self._cancel_events[task]
        runtime.install(
            cancelled=cancel.is_set,
            progress=lambda fraction, message: self._send_progress(task, fraction, message),
        )
        job_dir: Path | None = None
        owns_job_dir = False
        final: Outcome
        try:
            if cancel.is_set():  # cancelled before it even started (e.g. the host went away)
                raise T.Cancelled()
            tool_id = tool_id_from_script(script)
            if tool_id not in self.tools:
                raise T.ToolError(
                    "unknown_tool",
                    "only declared tools may be executed; got %r" % script[:SCRIPT_PREVIEW_CHARS],
                )
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

    def _tool_exit_outcome(self, script: str, error: BaseException) -> Outcome:
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
    def _tool_crash_outcome(script: str, error: BaseException) -> Outcome:
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

    def _execute(
        self, tool_id: str, inputs: dict[str, Any], job_dir: Path, cancel: threading.Event
    ) -> Outcome:
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

    def _send_progress(self, task: str, fraction: float | None, message: object) -> None:
        if task not in self._cancel_events:
            return  # the task is over
        fields: dict[str, Any] = {"message": str(message)}
        if fraction is not None:
            fields.update(current=_whole_percent(fraction), maximum=PROGRESS_MAXIMUM)
        self.channel.send(task, "UPDATE", **fields)
