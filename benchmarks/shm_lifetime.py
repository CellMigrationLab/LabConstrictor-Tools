#!/usr/bin/env python3
"""Small proofs about the life of a shared block on POSIX (run on Linux; macOS and Windows differ, see docs/PERF_SHARED_MEMORY.md).

    python benchmarks/shm_lifetime.py

T1  host killed (SIGKILL), its resource tracker alive      -> the tracker unlinks the block
T2  host and tracker both killed (whole process group)      -> the block LEAKS in /dev/shm (needs a sweep at the next start)
T3  unlink while a reader still maps the block              -> the reader keeps reading, memory is freed when the last map goes
T4  SharedMemory.close() while a numpy view exists          -> silent, and the view then segfaults (T4b: a plain mmap refuses)
T5  non-contiguous layer data (transpose, strided slice)    -> np.copyto into the block gives the same pixels as a TIFF round trip
"""

import os
import signal
import subprocess
import sys
import textwrap
import time
from multiprocessing import shared_memory
from pathlib import Path

import numpy as np

SHM = Path("/dev/shm")
results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print("%-4s %-4s %s" % (name, "PASS" if ok else "FAIL", detail))


def host_script(name: str) -> str:
    return textwrap.dedent("""
        import sys, time
        from multiprocessing import shared_memory
        b = shared_memory.SharedMemory(name=%r, create=True, size=1 << 20)
        print("ready", flush=True)
        time.sleep(60)
    """ % name)


def exists(name: str) -> bool:
    return (SHM / name).exists()


# T1: host SIGKILL, tracker alive
name = "lc_t1_%d" % os.getpid()
p = subprocess.Popen([sys.executable, "-c", host_script(name)], stdout=subprocess.PIPE, text=True)
p.stdout.readline()
before = exists(name)
os.kill(p.pid, signal.SIGKILL)
p.wait()
time.sleep(1.0)
check(
    "T1",
    before and not exists(name),
    "block existed while the host lived: %s; after SIGKILL of the host only: exists=%s"
    % (before, exists(name)),
)
(SHM / name).unlink(missing_ok=True)

# T2: host and tracker killed together (a host started in its own process group and killed as a group, like a crashed IDE/terminal)
name = "lc_t2_%d" % os.getpid()
p = subprocess.Popen(
    [sys.executable, "-c", host_script(name)], stdout=subprocess.PIPE, text=True, start_new_session=True
)
p.stdout.readline()
os.killpg(p.pid, signal.SIGKILL)
p.wait()
time.sleep(1.0)
leaked = exists(name)
check(
    "T2",
    leaked,
    "after SIGKILL of the whole group the block is still in /dev/shm: %s (so a start-up sweep is needed)"
    % leaked,
)
(SHM / name).unlink(missing_ok=True)

# T3: unlink while mapped
b = shared_memory.SharedMemory(create=True, size=1 << 20)
np.ndarray((1 << 20,), dtype=np.uint8, buffer=b.buf)[:] = 7
r = shared_memory.SharedMemory(name=b.name)
b.close()
b.unlink()
check(
    "T3",
    not exists(b.name) and int(np.ndarray((1 << 20,), dtype=np.uint8, buffer=r.buf)[123]) == 7,
    "name gone from /dev/shm, the attached reader still sees the pixels",
)
r.close()

# T4: SharedMemory.close() (and SharedMemory.__del__) with a live numpy view: no error, then the view is a dangling pointer
crash = subprocess.run(
    [
        sys.executable,
        "-c",
        textwrap.dedent("""
    import numpy as np
    from multiprocessing import shared_memory
    b = shared_memory.SharedMemory(create=True, size=1 << 20)
    v = np.ndarray((1 << 20,), dtype=np.uint8, buffer=b.buf)
    b.close()          # no BufferError on this Python
    print(v[5])        # reads unmapped memory
"""),
    ],
    capture_output=True,
    text=True,
)
check(
    "T4",
    crash.returncode == -signal.SIGSEGV,
    "SharedMemory.close() with a live view is silent, reading the view then ends the process with SIGSEGV (exit %d): a host that hands out a shared-memory array must keep the mapping alive with the array"
    % crash.returncode,
)

# T4b: a plain mmap keeps itself alive behind the array and refuses to close under it
import mmap

fd = os.open("/dev/shm/lc_t4b_%d" % os.getpid(), os.O_CREAT | os.O_RDWR, 0o600)
os.ftruncate(fd, 1 << 20)
m = mmap.mmap(fd, 1 << 20)
arr = np.frombuffer(m, dtype=np.uint8)
try:
    m.close()
    check("T4b", False, "mmap.close() under a live array did not raise")
except BufferError:
    check(
        "T4b",
        True,
        "mmap.close() under a live numpy array raises BufferError: an mmap-backed array is safe to hand to a viewer layer",
    )
del arr
m.close()
os.close(fd)
os.unlink("/dev/shm/lc_t4b_%d" % os.getpid())

# T5: non-contiguous input
rng = np.random.default_rng(0)
base = rng.integers(0, 65535, size=(600, 800), dtype=np.uint16)
for label, layer in (
    ("transpose", base.T),
    ("strided", base[::2, ::3]),
    ("fortran", np.asfortranarray(base)),
):
    blk = shared_memory.SharedMemory(create=True, size=layer.nbytes)
    dst = np.ndarray(
        layer.shape, dtype=layer.dtype, buffer=blk.buf
    )  # C order, the only order the descriptor can express
    np.copyto(dst, layer)
    ok = np.array_equal(dst, layer) and dst.flags["C_CONTIGUOUS"]
    del dst
    blk.close()
    blk.unlink()
    check("T5", ok, "%s layer copied into a C-ordered block, pixels identical" % label)

sys.exit(0 if all(results) else 1)
