"""Stress 2: parallel runs, churn, register/read races, stopped workers.  Uses a private LC_HOME and the example app."""

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import psutil

HOME = Path(tempfile.mkdtemp(prefix="lcstress_"))
os.environ["LC_HOME"] = str(HOME)
from labconstrictor_tools import client, registry

SYN = "labconstrictor_tools.examples.synthetic"
registry.register("synthetic", sys.prefix, SYN, "0")


def workers():
    return [
        p
        for p in psutil.process_iter(["cmdline"])
        if "labconstrictor_tools" in " ".join(p.info["cmdline"] or [])
        and "serve" in (p.info["cmdline"] or [])
    ]


R = {}

# a) 40 parallel CLI runs
t0 = time.time()
procs = [
    subprocess.Popen(
        [sys.executable, "-m", "labconstrictor_tools", "run", "synthetic", "scalar_echo", "a=%d" % i, "b=1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for i in range(40)
]
ok = sum(1 for p in procs if p.wait() == 0 and json.loads(p.stdout.read())["status"] == "COMPLETE")
log = HOME / "logs" / "labconstrictor.log"
lines = [
    ln for ln in log.read_text(errors="replace").splitlines() if ln and re.match(r"\d{4}-\d\d-\d\d ", ln)
]
bad = [
    ln
    for ln in log.read_text(errors="replace").splitlines()
    if ln and not re.match(r"(\d{4}-\d\d-\d\d |\s|Traceback|\w)", ln)
]
R["a_parallel_40"] = dict(
    complete=ok,
    seconds=round(time.time() - t0, 1),
    run_records=len(list((HOME / "runs").iterdir())),
    log_lines=len(lines),
    garbled_log_lines=len(bad),
    orphans=len(workers()),
)

# b) 500 sequential runs on one worker: leak check
w = client.WorkerProcess("synthetic")
wp = psutil.Process(w.proc.pid)
me = psutil.Process()


def snap():
    return dict(
        worker_rss_mb=wp.memory_info().rss >> 20,
        worker_fds=wp.num_fds(),
        worker_threads=wp.num_threads(),
        host_rss_mb=me.memory_info().rss >> 20,
        host_fds=me.num_fds(),
        host_threads=me.num_threads(),
    )


for _ in range(20):
    w.task("scalar_echo", {"a": 1, "b": 2}).wait(30)
start = snap()
t0 = time.time()
fails = 0
for i in range(500):
    t = w.task("scalar_echo", {"a": i, "b": 2}).wait(30)
    fails += t.status != "COMPLETE"
    if i % 100 == 99:
        w.tasks.clear()  # a host holds Task objects; clearing mimics the widgets' lifetime
R["b_churn_500"] = dict(
    start=start, end=snap(), seconds=round(time.time() - t0, 1), failures=fails, tasks_dict_len=len(w.tasks)
)
w.close()

# c) register/unregister while readers scan
errors, stop, reads = [], threading.Event(), [0]


def reader():
    while not stop.is_set():
        try:
            s, p = registry.load_schemas()
            reads[0] += 1
            for name in s:
                assert s[name]["protocol"] == 1
            for _, reason in p:
                if "unreadable" in reason or "Expecting" in reason:
                    errors.append(reason)
        except Exception as e:
            errors.append(repr(e))


threads = [threading.Thread(target=reader) for _ in range(4)]
[t.start() for t in threads]
for i in range(60):
    registry.register("racer", sys.prefix, SYN, str(i))
    registry.unregister("racer")
stop.set()
[t.join() for t in threads]
R["c_register_race"] = dict(reads=reads[0], reader_errors=len(errors), sample=errors[:3])

# d) stopped (hung) worker: Cancel, run_once timeout, host close
w = client.WorkerProcess("synthetic")
t = w.task("slow", {"seconds": 30})
t.launched.wait(10)
time.sleep(1)
os.kill(w.proc.pid, signal.SIGSTOP)
time.sleep(1)
t.cancel()
t0 = time.time()
t.wait(8)
R["d_sigstop_cancel_8s"] = dict(status=t.status, hung_task_finished=t.done.is_set())
t1 = time.time()
w.close(timeout=2)
R["d_sigstop_close_seconds"] = round(time.time() - t1, 1)
time.sleep(0.5)
R["d_alive_after_close"] = w.proc.poll() is None
# run_once timeout on a stopped worker is covered by kill(); SIGKILL works on stopped procs
try:
    os.kill(w.proc.pid, signal.SIGKILL)
except ProcessLookupError:
    pass
print(json.dumps(R, indent=1))
print("orphans at end:", len(workers()))
