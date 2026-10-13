"""Tools used by shm_bench.py: the smallest apps that separate "move the pixels" from "do the science".

Not a real app: no registration needed, `shm_bench.py` starts it with `WorkerProcess(module="shm_bench_app")`.
"""

from __future__ import annotations

import resource
import sys
from typing import Annotated

from labconstrictor_tools import Image, ImageOut, Name, Scalars, tool


def _rusage() -> dict:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is KiB on Linux, bytes on macOS
    scale = 1 if sys.platform != "darwin" else 1 / 1024
    return {"minflt": ru.ru_minflt, "majflt": ru.ru_majflt, "maxrss_kib": int(ru.ru_maxrss * scale)}


@tool("Probe")
def probe() -> Scalars:
    """Cumulative page faults and peak resident memory of this worker so far."""
    return _rusage()


@tool("Image max")
def image_max(image: Image) -> Scalars:
    """Input transport only: reads the whole image once (no copy), returns a number."""
    return {"max": int(image.max()), **_rusage()}


@tool("View max (zero copy)")
def view_max(block: str, rows: int, cols: int) -> Scalars:
    """PROTOTYPE of a borrowed read-only view (plan item 2): map the host's block, read it in place, never copy."""
    from multiprocessing import resource_tracker, shared_memory

    import numpy as np

    register = resource_tracker.register
    resource_tracker.register = (
        lambda *_a, **_k: None
    )  # attach without taking over the block (convert._attach_shared_memory does the same)
    try:
        shm = shared_memory.SharedMemory(name=block)
    finally:
        resource_tracker.register = register
    view = np.ndarray((rows, cols), dtype=np.uint16, buffer=shm.buf)
    view.flags.writeable = False
    result = int(view.max())
    del view
    shm.close()
    return {"max": result, **_rusage()}


@tool("Image checksum")
def image_checksum(image: Image) -> Scalars:
    """Sum of all pixels as an unsigned 64-bit integer, plus the first pixel (catches byte-order and signedness mistakes)."""
    import numpy as np

    return {
        "sum": int(image.astype(np.uint64).sum()),
        "first": int(image.flat[0]),
        "shape": list(image.shape),
        "dtype": str(image.dtype),
    }


@tool("Invert")
def invert(image: Image) -> Annotated[ImageOut, Name("inverted")]:
    """Round trip: one new array in the tool, written back as a TIFF by the worker (the current result path)."""
    import numpy as np

    return np.iinfo(image.dtype).max - image


@tool("Pass through")
def passthrough(image: Image) -> Annotated[ImageOut, Name("same")]:
    """No new array in the tool: isolates the result write (build_results) from the tool's own work."""
    return image


@tool("Invert to shared memory")
def invert_to_shm(image: Image) -> Scalars:
    """PROTOTYPE of a shared-memory result: the tool writes its result straight into a new block and returns the
    descriptor. Not part of the protocol today; used to price the return leg."""
    from multiprocessing import resource_tracker, shared_memory

    import numpy as np

    # the block must outlive this worker's resource tracker: do what convert._attach_shared_memory does, for creation
    register = resource_tracker.register
    resource_tracker.register = lambda *_a, **_k: None
    try:
        shm = shared_memory.SharedMemory(create=True, size=image.nbytes)
    finally:
        resource_tracker.register = register
    out = np.ndarray(image.shape, dtype=image.dtype, buffer=shm.buf)
    np.subtract(np.iinfo(image.dtype).max, image, out=out)
    descriptor = {
        "appose_type": "ndarray",
        "shm": {"name": shm.name},
        "shape": list(image.shape),
        "dtype": str(image.dtype),
    }
    del out
    shm.close()
    return {"descriptor": descriptor}
