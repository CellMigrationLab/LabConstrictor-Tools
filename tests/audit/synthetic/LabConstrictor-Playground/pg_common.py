"""Helpers of the Playground image datasets: writer, ramp, closed-form percentile and the count_above_level case. `put` and `ramp` are generic."""

from __future__ import annotations

import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (  # noqa: E402
    Suite,
    chk_status,
    chk_value,
    write_tiff,
)

BACKGROUND, FOREGROUND = 20, 200


def put(
    s: Suite,
    ident: str,
    data: np.ndarray,
    axes: str,
    *,
    px: tuple[float, float] | None = None,
    unit: str = "um",
    fmt: str = "imagej",
    z: float | None = None,
    t: float | None = None,
    ome: bool = False,
    folder: str = "",
) -> list[Path]:
    """Write fixtures/<folder>/<ident>.tif (and fixtures/ome/<ident>.ome.tif when `ome`); returns the files."""
    base = s.fixtures / folder / (ident + ".tif") if folder else s.fixtures / (ident + ".tif")
    files = [write_tiff(base, data, axes, pixel_um=px, unit=unit, fmt=fmt, z_um=z, t_s=t)]
    if ome and px is not None:
        files.append(
            write_tiff(
                s.fixtures / "ome" / (ident + ".tif"),
                data,
                axes,
                pixel_um=px,
                unit=unit,
                fmt="ome",
                z_um=z,
                t_s=t,
            )
        )
    return files


def ramp(shape: tuple[int, int], dtype: Any = np.uint16) -> np.ndarray:
    """Every row is 0, 1, ..., W-1."""
    return np.tile(np.arange(shape[1]), (shape[0], 1)).astype(dtype)


def linear_percentile(values_per_column: int, width: int, p: float) -> float:
    """numpy's default (linear) percentile of a ramp whose values 0..width-1 each occur `values_per_column` times, in closed form."""
    n = values_per_column * width
    pos = p / 100 * (n - 1)
    lo = int(math.floor(pos))
    a_lo, a_hi = lo // values_per_column, min(lo + 1, n - 1) // values_per_column
    return a_lo + (pos - lo) * (a_hi - a_lo)


def count_case(
    s: Suite,
    ident: str,
    purpose: str,
    files: Sequence[Path],
    inputs: dict[str, Any],
    pixels: int,
    level: float,
    total: int,
    derivation: str,
    outcome: str = "works",
) -> None:
    values = {"pixels": pixels, "level_used": level}
    s.dataset(
        ident,
        purpose,
        outcome,
        derivation=derivation,
        files=files,
        tool="count_above_level",
        inputs=inputs,
        expect={"results": {"values": {"pixels": pixels, "level_used": {"approx": level, "tol": 1e-4}}}},
        checks=[
            chk_status("COMPLETE"),
            chk_value("pixels", pixels),
            chk_value("level_used", level, 1e-4),
            chk_value("fraction", pixels / total, 1e-9),
        ],
        outcome_text="values %s" % values,
    )
