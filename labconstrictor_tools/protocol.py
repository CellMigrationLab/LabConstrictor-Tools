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
from collections.abc import Iterator
from typing import Any

TOOL_PREFIX = "lc:"
JOB_DIR_KEY = "_job_dir"  # reserved input: host-owned directory for outputs
TERMINAL = ("COMPLETION", "FAILURE", "CANCELATION")
MAX_REQUEST_BYTES = (
    16 * 1024 * 1024
)  # a request carries parameters and file references, never image data: refuse more


def tool_id_from_script(script: str) -> str | None:
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


def _encode(message: dict[str, Any]) -> str:
    """Strict JSON. NaN/Infinity are not JSON (other hosts cannot parse them): they travel as null, which PROTOCOL.md
    documents. Any other value that JSON cannot represent raises TypeError - it is never turned into text silently.
    """
    try:
        return json.dumps(message, allow_nan=False)
    except ValueError:
        return json.dumps(_finite(message), allow_nan=False)


class Channel:
    """Thread-safe writer of response lines on the worker's real stdout."""

    def __init__(self):
        self._out = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
        os.dup2(2, 1)  # stray prints from tools or libraries go to stderr
        sys.stdout = sys.stderr
        self._lock = threading.Lock()
        self._reported_closed = False

    def send(self, task: str, response_type: str, **fields: Any) -> None:
        message = {"task": task, "responseType": response_type, **fields}
        try:
            line = _encode(message)
        except TypeError as error:
            if response_type not in TERMINAL:
                raise
            print(
                "LabConstrictor worker: a %s message cannot be serialised: %s" % (response_type, error),
                file=sys.stderr,
                flush=True,
            )
            line = _encode(
                {
                    "task": task,
                    "responseType": "FAILURE",
                    "error": "[unserializable_result] the tool returned a value that cannot be sent to the host (%s)"
                    % error,
                    "code": "unserializable_result",
                }
            )
        with self._lock:
            try:
                self._out.write(line + "\n")
                self._out.flush()
            except (
                OSError
            ) as error:  # BrokenPipeError included: the host is gone, nobody to tell; stderr is what is left
                if not self._reported_closed:
                    self._reported_closed = True
                    print(
                        "LabConstrictor worker: cannot write to the host (%s: %s); the host is gone, further output is dropped"
                        % (type(error).__name__, error),
                        file=sys.stderr,
                        flush=True,
                    )

    @staticmethod
    def read_requests() -> Iterator[dict[str, Any]]:
        """Yield parsed request dicts from stdin until EOF; malformed lines are skipped (and reported on stderr)."""
        for line in _stdin_lines():
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except ValueError:
                print(
                    "LabConstrictor worker: ignoring a request line that is not JSON: %.200r" % line,
                    file=sys.stderr,
                    flush=True,
                )
                continue
            if not isinstance(request, dict):
                print(
                    "LabConstrictor worker: ignoring a request that is not an object: %.200r" % line,
                    file=sys.stderr,
                    flush=True,
                )
                continue
            yield request  # (a list/number/null line was skipped above: it must not kill the reader thread)


def _oversized(size: int) -> None:
    print(
        "LabConstrictor worker: ignoring a request line longer than %d bytes (%d read so far)"
        % (MAX_REQUEST_BYTES, size),
        file=sys.stderr,
        flush=True,
    )


def _stdin_lines():
    if os.name != "nt":
        yield from _bounded_lines(sys.stdin.readline)
        return
    yield from _stdin_lines_without_pending_read()


def _bounded_lines(readline, limit: int = MAX_REQUEST_BYTES) -> Iterator[str]:
    """Lines from `readline`, except that a line longer than `limit` is dropped (reported once) instead of buffered."""
    while True:
        line = readline(limit + 1)
        if not line:
            return
        if len(line) > limit and not line.endswith("\n"):
            _oversized(len(line))
            while line and not line.endswith("\n"):  # skip the rest of that line without keeping it
                line = readline(limit)
            continue
        yield line


class LineSplitter:
    """Bytes -> lines for the Windows reader, with the same size limit (a line without newline is dropped, not kept)."""

    def __init__(self, limit: int = MAX_REQUEST_BYTES) -> None:
        self.limit, self.buffer, self.dropping = limit, b"", False

    def feed(self, chunk: bytes) -> list[str]:
        out: list[str] = []
        *lines, rest = (self.buffer + chunk).split(b"\n")
        for raw in lines:
            if self.dropping:
                self.dropping = False  # the newline ended the oversized line
            elif len(raw) > self.limit:
                _oversized(len(raw))
            else:
                out.append(raw.decode("utf-8", errors="replace"))
        if len(rest) > self.limit:
            if not self.dropping:
                _oversized(len(rest))
            self.dropping, rest = True, b""
        self.buffer = rest
        return out

    def finish(self) -> list[str]:
        rest, self.buffer = self.buffer, b""
        return [rest.decode("utf-8", errors="replace")] if rest.strip() and not self.dropping else []


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
    splitter = LineSplitter()
    while True:
        available = wintypes.DWORD(0)
        if not kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(available), None):
            break  # broken pipe: the writer closed its end (EOF) or the handle is not a pipe
        if available.value:
            chunk = os.read(0, available.value)
            if not chunk:
                break
            yield from splitter.feed(chunk)
        else:
            time.sleep(poll_seconds)
    yield from splitter.finish()
