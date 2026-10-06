"""Tools for the worker-protocol tests: they misbehave on purpose."""

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
