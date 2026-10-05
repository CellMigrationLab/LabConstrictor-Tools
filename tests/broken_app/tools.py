"""Deliberately flawed tools: the `test` command must catch each of these."""

import time

from labconstrictor_tools import Image, ImageOut, Scalars, TableOut, tool


@tool("Returns the wrong number of outputs")
def bad_return(a: float = 1.0) -> tuple[Scalars, Scalars]:
    return ({"x": 1},)


@tool("Needs an image")
def needs_image(image: Image) -> Scalars:
    return {"ok": True}


@tool("Float64 image")
def fine_image(a: float = 1.0) -> ImageOut:
    import numpy as np

    return np.zeros((4, 4), dtype=np.float64)  # converted to float32 by the worker: must pass


@tool("Ignores cancel")
def deaf(seconds: float = 14.0) -> Scalars:
    time.sleep(seconds)
    return {"slept": seconds}


@tool("Empty table")
def empty_table(a: float = 1.0) -> TableOut:
    import pandas as pd

    return pd.DataFrame()
