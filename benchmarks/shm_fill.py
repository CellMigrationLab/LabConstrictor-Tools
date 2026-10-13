#!/usr/bin/env python3
"""How a host should fill a shared block: page-faulting through the mapping (what multiprocessing.shared_memory does and what
a Java MappedByteBuffer does) versus write() into the file descriptor versus MAP_POPULATE. Linux only (/dev/shm).

    python benchmarks/shm_fill.py --mb 512 --repeats 3
"""

import argparse
import mmap
import os
import statistics
import time
from multiprocessing import shared_memory

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mb", type=int, default=512)
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    n = args.mb * 1024 * 1024
    src = np.random.default_rng(0).integers(0, 255, size=n, dtype=np.uint8)
    results = {}
    for _ in range(args.repeats):
        # 1. SharedMemory + copy through the mapping
        t = time.perf_counter()
        b = shared_memory.SharedMemory(create=True, size=n)
        np.ndarray(src.shape, dtype=src.dtype, buffer=b.buf)[...] = src
        results.setdefault("mmap_fault_fill", []).append(time.perf_counter() - t)
        b.close()
        b.unlink()
        # 2. write() into the descriptor (no page faults in the writer), then map
        t = time.perf_counter()
        name = "/dev/shm/lc_fill_%d" % os.getpid()
        fd = os.open(name, os.O_CREAT | os.O_RDWR, 0o600)
        mv = memoryview(src)
        done = 0
        while done < n:
            done += os.write(fd, mv[done : done + (64 << 20)])
        results.setdefault("write_fd_fill", []).append(time.perf_counter() - t)
        os.close(fd)
        os.unlink(name)
        # 3. MAP_POPULATE: the kernel allocates every page up front, then memcpy
        t = time.perf_counter()
        fd = os.open(name, os.O_CREAT | os.O_RDWR, 0o600)
        os.ftruncate(fd, n)
        m = mmap.mmap(fd, n, flags=mmap.MAP_SHARED | getattr(mmap, "MAP_POPULATE", 0))
        np.frombuffer(m, dtype=np.uint8)[...] = src
        results.setdefault("map_populate_fill", []).append(time.perf_counter() - t)
        del m
        os.close(fd)
        os.unlink(name)
        # 4. the same copy into ordinary memory (the floor)
        t = time.perf_counter()
        dst = np.empty_like(src)
        dst[...] = src
        results.setdefault("anon_memory_copy", []).append(time.perf_counter() - t)
        del dst
    for key, xs in results.items():
        print(
            "%-18s %d MiB: median %.3f s  [%.3f..%.3f]"
            % (key, args.mb, statistics.median(xs), min(xs), max(xs))
        )


if __name__ == "__main__":
    main()
