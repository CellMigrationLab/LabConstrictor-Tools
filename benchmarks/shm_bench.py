#!/usr/bin/env python3
"""Measure how much a big image costs on the way host -> worker -> host: TIFF on disk versus shared memory.

Run (from a checkout of LabConstrictor-Tools, numpy + tifffile installed):

    python benchmarks/shm_bench.py --sizes 128 512 1024 --repeats 3 --json out.json
    python benchmarks/shm_bench.py --scratch /dev/shm/lc-bench ...   # when the disk has no room (then "disk" is tmpfs)
    python benchmarks/shm_bench.py --cold ...                        # drop the page cache before each task (needs root)

It plays the host (what Napari does: an in-memory array, `tifffile.imwrite` or a shared-memory block) against a real worker
(`python -m labconstrictor_tools serve`) running `shm_bench_app`. Every time is a wall-clock second measured by this process
except `load/tool/write`, which are the worker's own `timings` from COMPLETION. Image: uint16, 2-D, random, `MB` mebibytes.
Memory and page faults come from getrusage (worker: the `probe` tool, host: this process).
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import statistics
import sys
import tempfile
import time
from multiprocessing import shared_memory
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # run against the checkout, not an installed Tools
from labconstrictor_tools.client import WorkerProcess


def faults() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_minflt


def make_image(megabytes: int) -> np.ndarray:
    side = int((megabytes * 1024 * 1024 // 2) ** 0.5)
    return np.random.default_rng(0).integers(0, 65535, size=(side, side), dtype=np.uint16)


VMSTAT_KEYS = (
    "pgscan_direct",
    "pgscan_kswapd",
    "allocstall_normal",
    "pgsteal_direct",
    "pgpgout",
    "nr_written",
)


def telemetry() -> dict:
    """Kernel counters that say whether the machine was short of memory (Linux only; empty elsewhere)."""
    out: dict = {}
    try:
        for line in Path("/proc/vmstat").read_text().splitlines():
            key, _, value = line.partition(" ")
            if key in VMSTAT_KEYS:
                out[key] = int(value)
        some = Path("/proc/pressure/memory").read_text().splitlines()[0]
        out["psi_some_us"] = int(some.split("total=")[1])
    except (OSError, IndexError, ValueError):
        pass
    return out


def mem_available_mib() -> int:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 1 << 30


def start_guard(floor_mib: int, worker_ref: list) -> None:
    """Abort the run (kill the worker, remove the scratch folders) before the sandbox runs out of memory: nothing here may take
    down other work on a shared machine."""
    import threading

    def watch() -> None:
        while True:
            if mem_available_mib() < floor_mib:
                print("MemAvailable below %d MiB: aborting the benchmark" % floor_mib, flush=True)
                for w in worker_ref:
                    w.kill()
                shutil.rmtree(SCRATCH, ignore_errors=True)
                shutil.rmtree(OUT_SCRATCH, ignore_errors=True)
                os._exit(3)
            time.sleep(0.05)

    threading.Thread(target=watch, daemon=True).start()


def prewarm(megabytes: int) -> None:
    """Touch and free `megabytes` of fresh memory so the guest kernel has pages the hypervisor already backs. On a micro-VM
    (this sandbox) the first touch of memory the host has not backed costs 1-3 s per 512 MiB instead of 0.1 s; on a laptop this
    changes nothing. Called outside every timer, right before the step that allocates."""
    block = np.empty(megabytes * 1024 * 1024, dtype=np.uint8)
    block.fill(1)
    del block


def drop_caches() -> bool:
    try:
        os.sync()
        Path("/proc/sys/vm/drop_caches").write_text("3")
        return True
    except OSError:
        return False


def run_task(worker: WorkerProcess, tool: str, inputs: dict) -> tuple[float, dict]:
    t = time.perf_counter()
    task = worker.task(tool, inputs).wait(600)
    wall = time.perf_counter() - t
    if task.status != "COMPLETE":
        raise RuntimeError("%s: %s %s" % (tool, task.status, task.error))
    return wall, task.outputs


def values(outputs: dict) -> dict:
    for result in outputs["results"]:
        if result["type"] == "values":
            return result["values"]
    return {}


def worker_rusage(worker: WorkerProcess) -> dict:
    return values(run_task(worker, "probe", {"_job_dir": str(Path(tempfile.mkdtemp(dir=SCRATCH)))})[1])


def one_run(
    worker: WorkerProcess, image: np.ndarray, path_kind: str, tool: str, cold: bool, readback: bool = True
) -> dict:
    """One end-to-end task. path_kind: 'disk' or 'shm'. Returns every phase in seconds."""
    job = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="job_"))
    out_dir = Path(
        tempfile.mkdtemp(dir=OUT_SCRATCH, prefix="out_")
    )  # where the worker writes results (the host-owned _job_dir)
    row: dict = {"path": path_kind, "tool": tool}
    if PREWARM:
        prewarm(PREWARM * image.nbytes // (1024 * 1024))
    before = worker_rusage(worker)
    tele0, host_f0 = telemetry(), faults()
    block = None
    tif = job / "input.tif"
    # ---- host export
    t = time.perf_counter()
    if path_kind == "disk":
        tifffile.imwrite(tif, image)
        row["export_s"] = time.perf_counter() - t
        t = time.perf_counter()
        with open(tif, "rb") as handle:
            os.fsync(handle.fileno())
        row["export_fsync_s"] = time.perf_counter() - t  # what the disk still owed after imwrite returned
        value: object = str(tif)
    else:
        block = shared_memory.SharedMemory(create=True, size=image.nbytes)
        row["shm_create_s"] = time.perf_counter() - t
        t = time.perf_counter()
        np.ndarray(image.shape, dtype=image.dtype, buffer=block.buf)[...] = image
        row["shm_fill_s"] = time.perf_counter() - t
        row["export_s"] = row["shm_create_s"] + row["shm_fill_s"]
        value = {
            "appose_type": "ndarray",
            "shm": {"name": block.name},
            "shape": list(image.shape),
            "dtype": "uint16",
        }
    row["host_export_faults"] = faults() - host_f0
    if cold:
        row["cache_dropped"] = drop_caches()
    # ---- task
    if PREWARM:
        prewarm(PREWARM * image.nbytes // (1024 * 1024))
    if tool == "view_max":  # zero-copy prototype: the tool maps the block itself
        task_inputs = {
            "block": block.name,
            "rows": image.shape[0],
            "cols": image.shape[1],
            "_job_dir": str(out_dir),
        }
    else:
        task_inputs = {"image": value, "_job_dir": str(out_dir)}
    wall, outputs = run_task(worker, tool, task_inputs)
    timings = outputs["timings"]
    row["task_wall_s"] = wall
    row["load_s"], row["tool_s"], row["write_s"] = (
        timings["load_inputs_s"],
        timings["tool_s"],
        timings["write_results_s"],
    )
    row["transport_s"] = (
        wall - row["load_s"] - row["tool_s"] - row["write_s"]
    )  # pipes, JSON, scheduling, worker bookkeeping
    after = worker_rusage(worker)
    row["worker_faults"] = after["minflt"] - before["minflt"]
    row["worker_maxrss_mib"] = after["maxrss_kib"] // 1024
    # ---- result return
    if PREWARM and readback:
        prewarm(image.nbytes // (1024 * 1024))
    t = time.perf_counter()
    if not readback:
        if tool == "invert_to_shm":
            d = next(r for r in outputs["results"] if r["type"] == "values")["values"]["descriptor"]
            leftover = shared_memory.SharedMemory(name=d["shm"]["name"])
            leftover.close()
            leftover.unlink()
    elif tool in ("invert", "passthrough"):
        out_path = next(r["path"] for r in outputs["results"] if r["type"] == "image")
        result = tifffile.imread(out_path)
        row["result_read_s"] = time.perf_counter() - t
        assert result.shape == image.shape
        del result
    elif (
        tool == "invert_to_shm"
    ):  # (readback False would leak the block: the guard path never uses this tool)
        d = next(r for r in outputs["results"] if r["type"] == "values")["values"]["descriptor"]
        out = shared_memory.SharedMemory(name=d["shm"]["name"])
        view = np.ndarray(d["shape"], dtype=d["dtype"], buffer=out.buf)
        row["result_attach_s"] = time.perf_counter() - t  # zero-copy view: the host could display from this
        t = time.perf_counter()
        copy = view.copy()  # what a host that needs its own array (Napari layer) does
        row["result_copy_s"] = time.perf_counter() - t
        row["result_read_s"] = row["result_attach_s"] + row["result_copy_s"]
        del view, copy
        out.close()
        out.unlink()
    # ---- cleanup
    t = time.perf_counter()
    if block is not None:
        block.close()
        block.unlink()
    shutil.rmtree(job, ignore_errors=True)
    shutil.rmtree(out_dir, ignore_errors=True)
    row["cleanup_s"] = time.perf_counter() - t
    tele1 = telemetry()
    for key, value in tele1.items():
        row["k_" + key] = value - tele0.get(key, 0)  # kernel counters over the whole run
    row["total_s"] = (
        row["export_s"]
        + row.get("export_fsync_s", 0) * 0
        + row["task_wall_s"]
        + row.get("result_read_s", 0)
        + row["cleanup_s"]
    )
    return row


def cli_run(image: np.ndarray, tool: str, home: Path) -> dict:
    """The real command line: `labconstrictor-tools run APP TOOL image=FILE`, a new worker per call (cold start)."""
    import subprocess

    job = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="cli_"))
    tif = job / "input.tif"
    t = time.perf_counter()
    tifffile.imwrite(tif, image)
    export = time.perf_counter() - t
    env = dict(os.environ, LC_HOME=str(home), PYTHONPATH=str(HERE.parent), PYTHONSAFEPATH="")
    t = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "labconstrictor_tools",
            "run",
            "shm_bench",
            tool,
            "image=%s" % tif,
            "--out",
            str(job / "out"),
            "--no-record",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    wall = time.perf_counter() - t
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout + proc.stderr)
    shutil.rmtree(job, ignore_errors=True)
    return {"path": "cli", "tool": tool, "export_s": export, "cli_wall_s": wall}


def summarize(rows: list[dict]) -> dict:
    keys = sorted(
        {k for r in rows for k, v in r.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    )
    out = {}
    for k in keys:
        xs = [r[k] for r in rows if k in r]
        out[k] = {"median": statistics.median(xs), "min": min(xs), "max": max(xs)}
    return out


def main() -> None:
    global SCRATCH
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", type=int, nargs="+", default=[128, 512, 1024], help="image sizes in MiB")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--paths", nargs="+", default=["disk", "shm"], choices=["disk", "shm"])
    ap.add_argument(
        "--tools",
        nargs="+",
        default=["image_max", "invert"],
        choices=["image_max", "invert", "passthrough", "invert_to_shm", "view_max"],
    )
    ap.add_argument(
        "--scratch", default=None, help="folder for the files (default: a private folder under $TMPDIR)"
    )
    ap.add_argument(
        "--out-scratch",
        default=None,
        help="folder for the worker's result files (default: same as --scratch)",
    )
    ap.add_argument(
        "--cold", action="store_true", help="drop the page cache between export and task (root only)"
    )
    ap.add_argument(
        "--cli",
        action="store_true",
        help="also time the real `labconstrictor-tools run` (cold worker, disk path)",
    )
    ap.add_argument(
        "--prewarm",
        type=int,
        default=0,
        metavar="K",
        help="before the export and the task, touch and free K x image size of memory (micro-VM first-touch cost)",
    )
    ap.add_argument(
        "--no-readback",
        action="store_true",
        help="the host does not read the result back (saves memory at 1 GiB)",
    )
    ap.add_argument(
        "--guard-mib",
        type=int,
        default=700,
        help="abort when MemAvailable falls below this many MiB (0 = off)",
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    global OUT_SCRATCH, PREWARM
    PREWARM = args.prewarm
    SCRATCH = tempfile.mkdtemp(prefix="lc-shm-bench-", dir=args.scratch)
    OUT_SCRATCH = (
        tempfile.mkdtemp(prefix="lc-shm-out-", dir=args.out_scratch) if args.out_scratch else SCRATCH
    )
    results: dict = {
        "env": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "tifffile": tifffile.__version__,
            "cpus": os.cpu_count(),
            "scratch": SCRATCH,
            "out_scratch": OUT_SCRATCH,
            "cold": args.cold,
            "prewarm": args.prewarm,
        },
        "runs": {},
    }
    try:
        worker = WorkerProcess(module="shm_bench_app", pythonpath=[str(HERE)])
        if args.guard_mib:
            start_guard(args.guard_mib, [worker])
        run_task(worker, "probe", {"_job_dir": tempfile.mkdtemp(dir=SCRATCH)})  # warm the worker (imports)
        home = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="home_"))
        if args.cli:
            import subprocess

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "labconstrictor_tools",
                    "register",
                    "--name",
                    "shm_bench",
                    "--prefix",
                    sys.prefix,
                    "--module",
                    "shm_bench_app",
                    "--pythonpath",
                    str(HERE),
                ],
                env=dict(os.environ, LC_HOME=str(home), PYTHONPATH=str(HERE.parent)),
                check=True,
                capture_output=True,
            )
        for mb in args.sizes:
            image = make_image(mb)
            print("== %d MiB (%s, %s)" % (mb, image.shape, image.dtype), flush=True)
            for tool in args.tools:
                for kind in args.paths:
                    rows = []
                    for i in range(args.repeats):
                        rows.append(one_run(worker, image, kind, tool, args.cold, not args.no_readback))
                        r = rows[-1]
                        print(
                            "  %-9s %-5s run%d  export %.2f  task %.2f (load %.2f tool %.2f write %.2f other %.3f)  back %.2f  total %.2f  worker faults %d rss %d MiB  psi %dms scan %d"
                            % (
                                tool,
                                kind,
                                i + 1,
                                r["export_s"],
                                r["task_wall_s"],
                                r["load_s"],
                                r["tool_s"],
                                r["write_s"],
                                r["transport_s"],
                                r.get("result_read_s", 0),
                                r["total_s"],
                                r["worker_faults"],
                                r["worker_maxrss_mib"],
                                r.get("k_psi_some_us", 0) // 1000,
                                r.get("k_pgscan_direct", 0),
                            ),
                            flush=True,
                        )
                    results["runs"].setdefault(str(mb), {}).setdefault(tool, {})[kind] = {
                        "rows": rows,
                        "summary": summarize(rows),
                    }
            if args.cli:
                rows = [cli_run(image, "image_max", home) for _ in range(args.repeats)]
                results["runs"][str(mb)].setdefault("image_max", {})["cli"] = {
                    "rows": rows,
                    "summary": summarize(rows),
                }
                print("  cli image_max: %s" % [round(r["cli_wall_s"], 2) for r in rows], flush=True)
            del image
        worker.close()
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)
        shutil.rmtree(OUT_SCRATCH, ignore_errors=True)
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1))


SCRATCH = OUT_SCRATCH = ""
PREWARM = 0
if __name__ == "__main__":
    main()
