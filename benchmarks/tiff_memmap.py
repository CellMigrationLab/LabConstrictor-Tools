#!/usr/bin/env python3
"""The no-protocol-change alternative: the worker memory-maps the host's uncompressed TIFF instead of reading it
(`tifffile.memmap`, read-only). Compares imread (copy) with memmap for a tool that reads every pixel once.

    python benchmarks/tiff_memmap.py --mb 512 --repeats 3 --dir /path/on/disk [--cold]
"""

import argparse
import os
import statistics
import tempfile
import time
from pathlib import Path

import numpy as np
import tifffile


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mb", type=int, default=512)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--dir", default=tempfile.gettempdir())
    ap.add_argument("--cold", action="store_true", help="drop the page cache before each read (root, Linux)")
    args = ap.parse_args()
    side = int((args.mb * 1024 * 1024 // 2) ** 0.5)
    path = Path(args.dir) / "memmap_bench.tif"
    tifffile.imwrite(path, np.random.default_rng(0).integers(0, 65535, size=(side, side), dtype=np.uint16))
    with open(path, "rb") as handle:
        os.fsync(handle.fileno())
    out = {"imread": [], "memmap": []}
    for _ in range(args.repeats):
        for how in ("imread", "memmap"):
            if args.cold:
                os.sync()
                Path("/proc/sys/vm/drop_caches").write_text("3")
            fresh = np.empty(args.mb * 1024 * 1024, dtype=np.uint8)
            fresh.fill(1)
            del fresh  # warm memory, not timed
            t = time.perf_counter()
            array = tifffile.imread(path) if how == "imread" else tifffile.memmap(path, mode="r")
            load = time.perf_counter() - t
            t = time.perf_counter()
            int(array.max())
            use = time.perf_counter() - t
            out[how].append((load, use))
            del array
    print("%d MiB, %s cache" % (args.mb, "cold" if args.cold else "warm"))
    for how, rows in out.items():
        loads, uses = [r[0] for r in rows], [r[1] for r in rows]
        print(
            "  %-7s load %.3f [%.3f-%.3f]  first full pass %.3f [%.3f-%.3f]  load+pass %.3f"
            % (
                how,
                statistics.median(loads),
                min(loads),
                max(loads),
                statistics.median(uses),
                min(uses),
                max(uses),
                statistics.median(a + b for a, b in rows),
            )
        )
    path.unlink()


if __name__ == "__main__":
    main()
