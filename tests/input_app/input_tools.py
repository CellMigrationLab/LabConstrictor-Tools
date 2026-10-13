"""Tools for tests/test_input_loading.py: they report how the image arrived and misbehave with it on purpose. Only the tools live
here; reading the input is the worker's and the converter's job."""

import hashlib
import mmap

from labconstrictor_tools import Image, Scalars, tool


def _is_mapped(array) -> bool:
    base = array
    while base is not None:
        if isinstance(base, mmap.mmap):
            return True
        base = getattr(base, "base", None)
    return False


def _report(array) -> dict:
    return {
        "mapped": _is_mapped(array),
        "writeable": bool(array.flags.writeable),
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
        "plain_ndarray": type(array).__name__ == "ndarray",
    }


@tool("Report the input")
def report(image: Image) -> Scalars:
    return _report(image)


@tool("Overwrite the input")
def scribble(image: Image) -> Scalars:
    """Modifies its input in place, as tools written for an array in memory may do."""
    image[...] = 7
    return _report(image)


@tool("Fail while holding the input")
def fail_holding(image: Image) -> Scalars:
    """Raises with the input reachable from a reference cycle (a traceback and a cycle keep a mapping alive until collected)."""
    holder = {"image": image}
    holder["self"] = holder
    raise ValueError("on purpose: %s" % image.shape[0] + "" * len(holder))


@tool("Largest value")
def max_value(image: Image) -> Scalars:
    """Reads every pixel once (timing: the input transport plus one pass)."""
    return {"max": int(image.max()), "mapped": _is_mapped(image)}


@tool("Count the mappings of a file")
def mappings_of(path: str) -> Scalars:
    """Linux: how many memory mappings of `path` this process still has (the worker must have let go of a finished task's)."""
    import os

    if not os.path.exists("/proc/self/maps"):
        return {"mappings": -1}
    with open("/proc/self/maps", encoding="utf-8") as handle:
        return {"mappings": sum(1 for line in handle if os.path.realpath(path) in line)}
