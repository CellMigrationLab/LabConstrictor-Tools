"""Wire protocol: the Appose worker protocol subset spoken by `labconstrictor_tools` (JSON lines on stdin/stdout).

Requests  (host -> worker):  EXECUTE {task, script: "lc:<tool_id>", inputs}   |  CANCEL {task}
Responses (worker -> host):  LAUNCH | UPDATE {message, current, maximum} | COMPLETION {outputs}
                             | FAILURE {error, code, traceback?} | CANCELATION
Anything on the worker's real stdout other than these lines would corrupt the stream, so `Channel`
takes the real stdout for itself and redirects the process-wide stdout to stderr.
"""

import json
import math
import os
import sys
import threading

TOOL_PREFIX = "lc:"
JOB_DIR_KEY = "_job_dir"  # reserved input: host-owned directory for outputs
TERMINAL = ("COMPLETION", "FAILURE", "CANCELATION")


def tool_id_from_script(script):
    """`lc:<id>` -> `<id>`; anything else (e.g. Python source) -> None."""
    return script[len(TOOL_PREFIX) :] if script.startswith(TOOL_PREFIX) else None


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(v) for v in value]
    return value


class Channel:
    """Thread-safe writer of response lines on the worker's real stdout."""

    def __init__(self):
        self._out = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
        os.dup2(2, 1)  # stray prints from tools or libraries go to stderr
        sys.stdout = sys.stderr
        self._lock = threading.Lock()

    def send(self, task, response_type, **fields):
        message = {"task": task, "responseType": response_type, **fields}
        try:
            line = json.dumps(
                message, default=str, allow_nan=False
            )  # NaN/Infinity are not JSON: other hosts cannot parse them
        except ValueError:
            line = json.dumps(_finite(message), default=str, allow_nan=False)
        with self._lock:
            try:
                self._out.write(line + "\n")
                self._out.flush()
            except (BrokenPipeError, OSError):
                pass  # the host is gone: nobody to tell

    @staticmethod
    def read_requests():
        """Yield parsed request dicts from stdin until EOF; malformed lines are skipped."""
        for line in _stdin_lines():
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _stdin_lines():
    if os.name != "nt":
        yield from sys.stdin
        return
    yield from _stdin_lines_without_pending_read()


def _stdin_lines_without_pending_read(poll_seconds=0.02):
    """Windows: never leave a blocking ReadFile pending on the stdin handle.

    While a thread blocks in ReadFile on a synchronous pipe, any other code that queries that handle blocks too. Native
    libraries do this during initialisation (e.g. the Fortran runtime that scipy loads), so a tool importing scipy would
    hang forever (cf. numpy issue 24290). Instead poll with PeekNamedPipe and read only bytes that are already there.
    """
    import ctypes
    import msvcrt
    import time
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.PeekNamedPipe.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(0))
    buffer = b""
    while True:
        available = wintypes.DWORD(0)
        if not kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(available), None):
            break  # broken pipe: the writer closed its end (EOF) or the handle is not a pipe
        if available.value:
            chunk = os.read(0, available.value)
            if not chunk:
                break
            buffer += chunk
            *lines, buffer = buffer.split(b"\n")
            for raw in lines:
                yield raw.decode("utf-8", errors="replace")
        else:
            time.sleep(poll_seconds)
    if buffer.strip():
        yield buffer.decode("utf-8", errors="replace")
