#!/usr/bin/env python3
"""Where do the seconds go inside the worker for one big image? Replays the worker's steps one by one in a fresh process
and reports wall, user CPU, system CPU and page faults for each step (the "unexplained" worker time of issue #66).

    python benchmarks/shm_breakdown.py --mb 512 --repeats 3 --disk-dir /path/on/disk --tmp-dir /dev/shm

Steps (same calls as labconstrictor_tools.convert and worker._execute):
  attach        SharedMemory(name=...)                          (the host created and filled the block before)
  copy          np.ndarray(buffer=shm.buf).copy()               (convert._ndarray_from_shared_memory: the one worker copy)
  copy_warm     the same copy into memory that was already touched (what a reused buffer would cost: no page faults)
  tool          255 - image                                     (a tool that makes one new array: page faults on new memory)
  tiff_disk     tifffile.imwrite to --disk-dir                  (build_results for an image output)
  tiff_fsync    fsync of that file                              (what the disk still owes; a host does not wait for it)
  tiff_tmpfs    tifffile.imwrite to --tmp-dir (RAM)             (the same CPU work without a disk)
  tiff_read     tifffile.imread of the disk file (page cache)   (what a host does with a result)
"""

import argparse
import json
import os
import resource
import statistics
import tempfile
import time
from multiprocessing import shared_memory
from pathlib import Path

import numpy as np
import tifffile

PREWARM_MIB = 0


def measure(fn):
    if (
        PREWARM_MIB
    ):  # touch and free fresh memory first (outside the timer): on a micro-VM the guest then reuses pages the host already backs
        block = np.empty(PREWARM_MIB * 1024 * 1024, dtype=np.uint8)
        block.fill(1)
        del block
    r0, t0 = resource.getrusage(resource.RUSAGE_SELF), time.perf_counter()
    value = fn()
    t1, r1 = time.perf_counter(), resource.getrusage(resource.RUSAGE_SELF)
    return value, {
        "wall_s": t1 - t0,
        "user_s": r1.ru_utime - r0.ru_utime,
        "sys_s": r1.ru_stime - r0.ru_stime,
        "faults": r1.ru_minflt - r0.ru_minflt,
    }


def once(mb: int, disk_dir: str, tmp_dir: str) -> dict:
    side = int((mb * 1024 * 1024 // 2) ** 0.5)
    src = np.random.default_rng(0).integers(0, 65535, size=(side, side), dtype=np.uint16)
    block = shared_memory.SharedMemory(create=True, size=src.nbytes)
    np.ndarray(src.shape, dtype=src.dtype, buffer=block.buf)[...] = src
    out: dict = {}
    attached, out["attach"] = measure(lambda: shared_memory.SharedMemory(name=block.name))
    view = np.ndarray(src.shape, dtype=src.dtype, buffer=attached.buf)
    image, out["copy"] = measure(view.copy)
    _, out["copy_warm"] = measure(lambda: np.copyto(image, view))
    result, out["tool"] = measure(lambda: np.iinfo(image.dtype).max - image)
    path = Path(disk_dir) / "breakdown.tif"
    _, out["tiff_disk"] = measure(lambda: tifffile.imwrite(path, result))

    def sync():
        with open(path, "rb") as handle:
            os.fsync(handle.fileno())

    _, out["tiff_fsync"] = measure(sync)
    path2 = Path(tmp_dir) / "breakdown.tif"
    _, out["tiff_tmpfs"] = measure(lambda: tifffile.imwrite(path2, result))
    back, out["tiff_read"] = measure(lambda: tifffile.imread(path))
    out["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    del back
    view = None  # release the mapping before close()
    attached.close()
    block.close()
    block.unlink()
    path.unlink()
    path2.unlink()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mb", type=int, default=512)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--disk-dir", default=tempfile.gettempdir())
    ap.add_argument("--tmp-dir", default="/dev/shm" if os.path.isdir("/dev/shm") else tempfile.gettempdir())
    ap.add_argument(
        "--prewarm",
        action="store_true",
        help="touch and free one image's worth of memory before every step (not timed)",
    )
    ap.add_argument("--json")
    args = ap.parse_args()
    global PREWARM_MIB
    PREWARM_MIB = args.mb if args.prewarm else 0
    runs = [once(args.mb, args.disk_dir, args.tmp_dir) for _ in range(args.repeats)]
    print(
        "%d MiB, %d repeats (median [min..max]); wall / user / sys seconds, page faults"
        % (args.mb, args.repeats)
    )
    summary = {}
    for step in runs[0]:
        if step == "peak_rss_mib":
            print("  peak RSS %s MiB" % [r[step] for r in runs])
            continue
        row = {k: [r[step][k] for r in runs] for k in runs[0][step]}
        summary[step] = {k: statistics.median(v) for k, v in row.items()}
        print(
            "  %-11s wall %.3f [%.3f..%.3f]  user %.3f  sys %.3f  faults %d"
            % (
                step,
                summary[step]["wall_s"],
                min(row["wall_s"]),
                max(row["wall_s"]),
                summary[step]["user_s"],
                summary[step]["sys_s"],
                summary[step]["faults"],
            )
        )
    if args.json:
        Path(args.json).write_text(json.dumps({"mb": args.mb, "runs": runs, "median": summary}, indent=1))


if __name__ == "__main__":
    main()
