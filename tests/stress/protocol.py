"""Stress 3: protocol fuzzing and hostile tools against a raw worker / the client. Private LC_HOME."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

os.environ["LC_HOME"] = tempfile.mkdtemp(prefix="lcfuzz_")
HERE = str(Path(__file__).resolve().parent)
from labconstrictor_tools import client  # noqa: E402

R = {}
env = {
    **os.environ,
    "PYTHONPATH": os.pathsep.join([str(Path(HERE).parents[1]), HERE]),
    "PYTHONUNBUFFERED": "1",
}


def raw_worker():
    return subprocess.Popen(
        [sys.executable, "-m", "labconstrictor_tools", "serve", "--module", "hostile_tools"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env,
    )  # fmt: skip


def exchange(p, task="t1", tool="slow", inputs=None, timeout=15):
    p.stdin.write(
        (
            json.dumps(
                {
                    "task": task,
                    "requestType": "EXECUTE",
                    "script": "lc:" + tool,
                    "inputs": inputs or {"seconds": 0.1},
                }
            )
            + "\n"
        ).encode()
    )
    p.stdin.flush()
    end = time.time() + timeout
    while time.time() < end:
        line = p.stdout.readline()
        if not line:
            return "worker closed stdout"
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("task") == task and m.get("responseType") in ("COMPLETION", "FAILURE", "CANCELATION"):
            return m["responseType"]
    return "timeout"


# a) garbage on stdin, then a valid task must still work
p = raw_worker()
junk = [
    b"\x00\xff\xfe\x80 binary\n", b"{not json\n", b"[1,2,3]\n", b"42\n", b'"str"\n', b"null\n", b"\n\n\n",
    json.dumps({"task": "j1", "requestType": "EXECUTE", "script": 5, "inputs": {}}).encode() + b"\n",
    json.dumps({"task": "j2", "requestType": "EXECUTE", "script": "lc:slow", "inputs": [1, 2]}).encode() + b"\n",
    json.dumps({"task": "j3", "requestType": "EXECUTE", "script": "print('pwn')", "inputs": {}}).encode() + b"\n",
    json.dumps({"task": "j4", "requestType": "EXECUTE", "script": "lc:../../etc/passwd", "inputs": {}}).encode() + b"\n",
    json.dumps({"task": "j5", "requestType": "EXECUTE", "script": "lc:slow", "inputs": {"seconds": "abc"}}).encode() + b"\n",
    json.dumps({"task": "j6", "requestType": "EXECUTE", "script": "lc:slow", "inputs": {"_job_dir": "/proc/nope/x", "seconds": 0.1}}).encode() + b"\n",
    json.dumps({"task": "zz", "requestType": "CANCEL"}).encode() + b"\n",
    b"x" * 20_000_000 + b"\n",  # one 20 MB line
]  # fmt: skip
for j in junk:
    p.stdin.write(j)
p.stdin.flush()
time.sleep(1)
print("stage a: sent junk", flush=True)
R["a_valid_task_after_garbage"] = exchange(p, "good")
R["a_worker_alive"] = p.poll() is None
p.stdin.close()
p.wait(15)

# b) flood stdout / forged protocol line on fd 1 / huge result / daemon child / _exit
print("stage b", flush=True)
w = client.WorkerProcess(module="hostile_tools", pythonpath=[HERE])
for name, tool, inputs, wait in (
    ("b_flood_stdout_50MB", "flood_stdout", {"megabytes": 50}, 60),
    ("b_forged_fd1_lines", "raw_fd1", {}, 20),
    ("b_huge_result_100MB", "huge_result", {"megabytes": 100}, 90),
):
    t0 = time.time()
    t = w.task(tool, inputs).wait(wait)
    R[name] = dict(
        status=t.status, seconds=round(time.time() - t0, 1), error=(t.error or "")[:120], worker_alive=w.alive
    )
    if not w.alive:
        w = client.WorkerProcess(module="hostile_tools", pythonpath=[HERE])
t = w.task("daemon_child", {}).wait(20)
pid = t.outputs["results"][0]["values"]["child_pid"]
w.close()
time.sleep(1)
R["b_daemon_child_survives_worker_close"] = (
    psutil.pid_exists(pid) and psutil.Process(pid).status() != "zombie"
)
if psutil.pid_exists(pid):
    psutil.Process(pid).kill()
w = client.WorkerProcess(module="hostile_tools", pythonpath=[HERE])
t = w.task("exit_mid_task", {}).wait(20)
R["b_exit_mid_task"] = dict(status=t.status, error=(t.error or "")[:100])
w.close()

# c) stderr flood: host memory
w = client.WorkerProcess(module="hostile_tools", pythonpath=[HERE])
me = psutil.Process()
before = me.memory_info().rss >> 20
t0 = time.time()
t = w.task("flood_stderr", {"megabytes": 200}).wait(120)
R["c_flood_stderr_200MB"] = dict(
    status=t.status,
    seconds=round(time.time() - t0, 1),
    host_rss_before_mb=before,
    host_rss_after_mb=me.memory_info().rss >> 20,
    kept_stderr_chars=sum(map(len, w.stderr)),
)
w.close()

# d) deadlocked tool + Cancel through the client only (no host escalation) and close()
w = client.WorkerProcess(module="hostile_tools", pythonpath=[HERE])
t = w.task("deadlock", {})
t.launched.wait(10)
t.cancel()
t.wait(5)
R["d_deadlock_after_cancel_5s"] = t.status
t1 = time.time()
w.close(timeout=2)
R["d_close_seconds"] = round(time.time() - t1, 1)
R["d_alive_after_close"] = w.proc.poll() is None

print(json.dumps(R, indent=1))
