"""Tools for the worker-protocol tests: they misbehave on purpose."""

import os
import sys
import time

from labconstrictor_tools import Scalars, tool


@tool("Exits")
def exits(a: float = 1.0) -> Scalars:
    sys.exit(2)


@tool("Defaults matter")
def defaults(x: float = 7.0) -> Scalars:
    return {"x": x}


@tool("Waits")
def waits(seconds: float = 1.0) -> Scalars:
    time.sleep(seconds)
    return {"slept": seconds}


@tool("Returns an object JSON cannot carry")
def odd(a: float = 1.0) -> Scalars:
    return {"bad": {1, 2, 3}}


@tool("Returns NaN")
def nan(a: float = 1.0) -> Scalars:
    return {"v": float("nan")}


@tool("Records that it ran")
def records_call(sigma: float = 2.0) -> Scalars:
    """Appends the sigma it received to the file named by LC_CALL_LOG: proof that the tool body ran (or did not)."""
    with open(os.environ["LC_CALL_LOG"], "a", encoding="utf-8") as log:
        log.write("sigma=%s\n" % sigma)
    return {"sigma": sigma}
