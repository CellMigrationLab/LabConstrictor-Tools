"""Tools that misbehave on purpose (used by protocol.py)."""

import os
import subprocess
import sys
import time

from labconstrictor_tools import Scalars, check_cancel, tool


@tool("Flood stdout")
def flood_stdout(megabytes: int = 50) -> Scalars:
    for _ in range(megabytes):
        sys.stdout.write("x" * 1048575 + "\n")
    return {"ok": True}


@tool("Write raw fd 1")
def raw_fd1() -> Scalars:
    os.write(
        1, b'{"task": "x", "responseType": "COMPLETION", "outputs": {"results": []}}\n'
    )  # forged protocol line
    os.write(1, b"\xff\xfe not json at all\n")
    return {"ok": True}


@tool("Flood stderr")
def flood_stderr(megabytes: int = 200) -> Scalars:
    for _ in range(megabytes):
        sys.stderr.write("e" * 1048575 + "\n")
    return {"ok": True}


@tool("Huge result")
def huge_result(megabytes: int = 100) -> Scalars:
    return {"blob": "y" * (megabytes * 1048576)}


@tool("Daemon child")
def daemon_child() -> Scalars:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], start_new_session=True)
    return {"child_pid": child.pid}


@tool("Exit mid task")
def exit_mid_task() -> Scalars:
    os._exit(0)


@tool("Deadlock ignoring cancel")
def deadlock() -> Scalars:
    import signal

    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(1)


@tool("Slow cooperative")
def slow(seconds: float = 20.0) -> Scalars:
    end = time.time() + seconds
    while time.time() < end:
        check_cancel()
        time.sleep(0.05)
    return {"done": True}
