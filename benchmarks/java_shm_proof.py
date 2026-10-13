#!/usr/bin/env python3
"""Run a Java process that creates a shared block with a short[] image, then let the REAL LabConstrictor worker read it.

    python benchmarks/java_shm_proof.py --mode appose --classpath DIR_WITH_COMPILED_CLASSES:jna.jar:jna-platform.jar
    python benchmarks/java_shm_proof.py --mode mmap   --classpath DIR
    python benchmarks/java_shm_proof.py --mode ffm    --classpath DIR   (ShmProofFfm, Java 21 --enable-preview)

Passes when the worker's `image_checksum` equals the sum and first pixel Java computed: the pixels, their byte order and their unsigned values
survived Java heap -> block -> worker copy. Exit code 0 = pass.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from labconstrictor_tools.client import WorkerProcess


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["appose", "mmap", "ffm"], required=True)
    ap.add_argument("--classpath", required=True)
    ap.add_argument("--side", type=int, default=4096)
    args = ap.parse_args()
    cmd = ["java", "-Dside=%d" % args.side, "-Xmx3g"]
    main_class = "ShmProof"
    if args.mode == "ffm":
        cmd += ["--enable-preview"]
        main_class = "ShmProofFfm"
    cmd += ["-cp", args.classpath, main_class] + ([args.mode] if args.mode != "ffm" else [])
    java = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        line = java.stdout.readline()
        info = json.loads(line)
        descriptor = {
            "appose_type": "ndarray",
            "shm": {"name": info["name"]},
            "shape": info["shape"],
            "dtype": info["dtype"],
        }
        with WorkerProcess(module="shm_bench_app", pythonpath=[str(HERE)]) as worker:
            task = worker.task("image_checksum", {"image": descriptor, "_job_dir": tempfile.mkdtemp()}).wait(
                60
            )
        values = next(r["values"] for r in task.outputs["results"] if r["type"] == "values")
        ok = (
            values["sum"] == info["sum"]
            and values["first"] == info["first"]
            and values["shape"] == info["shape"]
        )
        print(
            "%s: java sum %d first %d, worker sum %d first %d, java fill %.3f s -> %s"
            % (
                info["mode"],
                info["sum"],
                info["first"],
                values["sum"],
                values["first"],
                info["fill_s"],
                "PASS" if ok else "FAIL",
            )
        )
        return 0 if ok else 1
    finally:
        java.stdin.write("done\n")
        java.stdin.close()
        java.wait(10)


if __name__ == "__main__":
    sys.exit(main())
