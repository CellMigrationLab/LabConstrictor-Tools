"""Tools that misbehave on purpose, for tests/test_roundtrip_failures.py: crashes, wrong returns, hangs, noise, floods, children.
Only the tools live here; the behaviour under test is the worker's and the client's."""

import os
import signal
import subprocess
import sys
import time
from typing import Annotated, Literal

from labconstrictor_tools import (
    ImageOut,
    Max,
    Min,
    Name,
    PointsOut,
    Scalars,
    TableOut,
    ToolError,
    check_cancel,
    progress,
    tool,
)

CHILD = [sys.executable, "-c", "import time; time.sleep(300)"]


def _start_child(pid_file: str) -> None:
    """A subprocess that would outlive the worker if nobody stopped it; its pid is written for the test to look at."""
    if pid_file:
        child = subprocess.Popen(CHILD)  # noqa: S603 - fixed argument list
        with open(pid_file, "w", encoding="utf-8") as handle:
            handle.write(str(child.pid))


@tool("Crash in the middle")
def crash_mid_task(how: Literal["exit", "kill"] = "exit", child_pid_file: str = "") -> Scalars:
    """Reports progress, then the process ends without a word (os._exit, or SIGKILL where there is one)."""
    _start_child(child_pid_file)
    progress(0.5, "halfway")
    time.sleep(0.2)
    if how == "kill" and hasattr(signal, "SIGKILL"):
        os.kill(os.getpid(), signal.SIGKILL)
    os._exit(7)


@tool("Raise a ToolError")
def raise_tool_error() -> Scalars:
    raise ToolError("my_code", "a readable message with unicode é and a second\nline")


@tool("Raise something unexpected")
def raise_unexpected(
    kind: Literal["zero", "memory", "system_exit", "keyboard", "multiline"] = "zero",
) -> Scalars:
    if kind == "zero":
        return {"x": 1 // 0}
    if kind == "memory":
        raise MemoryError("pretend the machine is full")
    if kind == "system_exit":
        sys.exit(3)
    if kind == "keyboard":
        raise KeyboardInterrupt
    raise RuntimeError("first line\nsecond line µm\n\ttabbed")


@tool("Return a string as an image")
def wrong_type_image() -> Annotated[ImageOut, Name("image")]:
    return "this is not an array"  # type: ignore[return-value]


@tool("Return a number as a table")
def wrong_type_table() -> Annotated[TableOut, Name("table")]:
    return 5  # type: ignore[return-value]


@tool("Return a list as scalars")
def wrong_type_scalars() -> Scalars:
    return [1, 2, 3]  # type: ignore[return-value]


@tool("Return text as points")
def wrong_type_points() -> PointsOut:
    return "no points here"  # type: ignore[return-value]


@tool("Return one value for two outputs")
def wrong_count_too_few() -> tuple[Annotated[ImageOut, Name("image")], Annotated[TableOut, Name("table")]]:
    return (__import__("numpy").zeros((2, 2), "uint8"),)  # type: ignore[return-value]


@tool("Return three values for two outputs")
def wrong_count_too_many() -> tuple[Annotated[ImageOut, Name("image")], Annotated[TableOut, Name("table")]]:
    import numpy as np

    return (np.zeros((2, 2), "uint8"), {"a": [1]}, 3)  # type: ignore[return-value]


@tool("Return nothing for two outputs")
def wrong_count_none() -> tuple[Annotated[ImageOut, Name("image")], Annotated[TableOut, Name("table")]]:
    return None  # type: ignore[return-value]


@tool("Return an array for two outputs")
def wrong_count_one_array() -> tuple[Annotated[ImageOut, Name("image")], Annotated[TableOut, Name("table")]]:
    return __import__("numpy").zeros((2, 2), "uint8")  # type: ignore[return-value]


@tool("Return a tuple for one output")
def wrong_count_tuple_for_one() -> Scalars:
    return ({"a": 1}, {"b": 2})  # type: ignore[return-value]


@tool("Cooperative hang")
def hang(seconds: Annotated[float, Min(0.1), Max(600)] = 120.0, child_pid_file: str = "") -> Scalars:
    """Runs for a long time but checks for Cancel."""
    _start_child(child_pid_file)
    end = time.time() + seconds
    while time.time() < end:
        check_cancel()
        progress(None, "waiting")
        time.sleep(0.05)
    return {"waited": seconds}


@tool("Deaf hang")
def deaf_hang(seconds: Annotated[float, Min(0.1), Max(600)] = 120.0, child_pid_file: str = "") -> Scalars:
    """Runs for a long time and never looks at Cancel (like a long call into C code)."""
    _start_child(child_pid_file)
    time.sleep(seconds)
    return {"waited": seconds}


@tool("Unserialisable result")
def unserialisable(kind: Literal["set", "object", "bytes", "complex"] = "set") -> Scalars:
    return {
        "set": {"x": {1, 2}},
        "object": {"x": object()},
        "bytes": {"x": b"raw"},
        "complex": {"x": 1 + 2j},
    }[kind]


@tool("Huge result")
def huge_output(megabytes: Annotated[int, Min(1), Max(200)] = 30) -> Scalars:
    return {"text": "x" * (megabytes * 1_000_000), "n": megabytes}


@tool("Noise on stdout")
def noisy(kind: Literal["print", "write", "raw_fd", "child", "flush_partial"] = "print") -> Scalars:
    """Everything a tool may write to standard output: it must never reach the protocol stream."""
    if kind == "print":
        print("NOISE print\n", "NOISE second line", sep="")
    elif kind == "write":
        sys.stdout.write("NOISE write without newline")
        sys.stdout.flush()
    elif kind == "raw_fd":
        os.write(1, b'NOISE raw bytes {"task": "x", "responseType": "COMPLETION"}\n')
    elif kind == "child":
        subprocess.run(
            [sys.executable, "-c", "print('NOISE from a child process')"], check=True
        )  # noqa: S603
    else:
        sys.stdout.write('{"task": "broken", "responseType"')
        sys.stdout.flush()
    return {"kind": kind}


@tool("Flood stderr")
def flood_stderr(megabytes: Annotated[int, Min(1), Max(500)] = 20) -> Scalars:
    line = "E" * 99 + "\n"
    for _ in range(megabytes * 10_000):
        sys.stderr.write(line)
    sys.stderr.write("LAST LINE OF THE FLOOD\n")
    sys.stderr.flush()
    return {"megabytes": megabytes}


@tool("Many progress messages")
def many_progress(n: Annotated[int, Min(1), Max(1_000_000)] = 20000) -> Scalars:
    for i in range(n):
        progress(i / n, "step %d" % i)
    return {"n": n}


@tool("Report one progress value")
def report_progress(fraction: Annotated[float, Min(0), Max(1)]) -> Scalars:
    progress(fraction, "reporting %r" % fraction)
    return {"fraction": fraction}


@tool("Leave a child behind")
def leave_child(child_pid_file: str) -> Scalars:
    """Returns normally while a subprocess it started is still running."""
    _start_child(child_pid_file)
    return {"started": True}


@tool("Echo")
def echo(value: int = 1) -> Scalars:
    return {"value": value}
