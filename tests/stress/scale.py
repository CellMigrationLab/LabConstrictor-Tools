"""Stress 1: image size vs time, peak RSS of the worker and the host, temp-disk use.  python scale.py SIZE_MB [tool]"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time

import psutil
import tifffile

from labconstrictor_tools import client


def make(mb, path):
    side = int((mb * 1024 * 1024 / 2) ** 0.5)
    m = tifffile.memmap(path, shape=(side, side), dtype="uint16")
    m[:] = 7
    m[::97] = 1000
    m.flush()
    del m
    return side


def run(mb, tool="image_stats"):
    d = tempfile.mkdtemp(prefix="stress_")
    p = os.path.join(d, "big.tif")
    side = make(mb, p)
    me = psutil.Process()
    peak = {"worker": 0, "host": 0}
    stop = threading.Event()
    w = client.WorkerProcess("synthetic")
    wp = psutil.Process(w.proc.pid)

    def sample():
        while not stop.is_set():
            try:
                peak["worker"] = max(peak["worker"], wp.memory_info().rss)
                peak["host"] = max(peak["host"], me.memory_info().rss)
            except psutil.Error:
                pass
            time.sleep(0.05)

    threading.Thread(target=sample, daemon=True).start()
    inputs = {"image": p} if tool == "image_stats" else {"required_string": "x", "image": p}
    t0 = time.time()
    t = w.task(tool, inputs).wait(900)
    dt = time.time() - t0
    stop.set()
    jd = (t.outputs or {}).get("job_dir")
    out = sum(os.path.getsize(os.path.join(jd, f)) for f in os.listdir(jd)) if jd and os.path.isdir(jd) else 0
    res = dict(
        file_mb=mb,
        side=side,
        tool=tool,
        status=t.status,
        seconds=round(dt, 1),
        worker_peak_mb=peak["worker"] >> 20,
        host_peak_mb=peak["host"] >> 20,
        output_mb=out >> 20,
        error=(t.error or "")[:200],
    )
    w.close()
    shutil.rmtree(d, ignore_errors=True)
    if jd and tool != "image_stats":
        shutil.rmtree(jd, ignore_errors=True)
    print(json.dumps(res), flush=True)


if __name__ == "__main__":
    run(int(sys.argv[1]), *(sys.argv[2:3]))
