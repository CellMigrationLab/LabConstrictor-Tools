"""Synthetic tools exercising every schema type, progress, cancellation and errors. numpy, pandas and tifffile are only needed when a tool that uses them runs."""

import time
from pathlib import Path
from typing import Annotated, Literal

from labconstrictor_tools import (
    Axes,
    Description,
    Image,
    ImageOut,
    Max,
    Min,
    Name,
    PixelSizeOf,
    Scalars,
    Table,
    TableOut,
    ToolError,
    Unit,
    check_cancel,
    progress,
    tool,
)


@tool("Kitchen sink")
def kitchen_sink(
    required_string: str,
    image: Image,
    optional_image: Image | None = None,
    optional_string: str | None = None,
    count: Annotated[int, Min(1), Max(10), Description("how many rows")] = 3,
    scale: Annotated[float, Min(0), Unit("um/px"), PixelSizeOf("image")] = 0.5,
    flag: bool = True,
    mode: Literal["alpha", "beta", "gamma"] = "beta",
    some_file: Path | None = None,
) -> tuple[
    Annotated[ImageOut, Name("doubled")],
    Annotated[TableOut, Name("rows")],
    Annotated[Scalars, Name("summary")],
]:
    """Echoes its inputs in every output type."""
    import pandas as pd

    rows = pd.DataFrame({"i": range(count), "s": [required_string] * count, "scale": [scale] * count})
    return (
        image * 2,
        rows,
        {
            "mode": mode,
            "flag": flag,
            "optional_string": optional_string,
            "had_optional_image": optional_image is not None,
            "file": str(some_file) if some_file else None,
            "shape": list(image.shape),
        },
    )


@tool("Slow with progress")
def slow(
    seconds: Annotated[float, Min(0.1), Max(60), Unit("s")] = 3.0, steps: Annotated[int, Min(1), Max(100)] = 6
) -> Scalars:
    """Cooperative long-running task: reports progress and honours Cancel."""
    for i in range(steps):
        check_cancel()
        progress(i / steps, "step %d of %d" % (i + 1, steps))
        time.sleep(seconds / steps)
    progress(1.0, "done")
    return {"steps": steps}


@tool("Stubborn (ignores cancel)")
def stubborn(seconds: Annotated[float, Min(0.1)] = 30.0) -> Scalars:
    """Blocks without checking for cancellation, like a long C extension call. Hosts must kill the worker."""
    time.sleep(seconds)
    return {"slept": seconds}


@tool("Explode")
def explode(kind: Literal["tool_error", "exception"] = "tool_error") -> Scalars:
    """Always fails."""
    if kind == "tool_error":
        raise ToolError("expected_failure", "this tool always fails (kind=tool_error)")
    return {"x": 1 // 0}


@tool("Scalar echo")
def scalar_echo(a: float = 1.0, b: float = 2.0) -> Scalars:
    return {"sum": a + b}


@tool("Table sum")
def table_sum(tab: Table) -> Scalars:
    return {"columns": list(tab.columns), "total": float(tab.select_dtypes("number").sum().sum())}


@tool("Image stats")
def image_stats(image: Image) -> Scalars:
    """Returns shape/dtype/mean of the received image (measures input transfer cost only)."""
    return {"shape": list(image.shape), "dtype": str(image.dtype), "mean": float(image.mean())}


@tool("Unicode echo")
def unicode_echo(text: str = "µm → ✓ naïve") -> Scalars:
    """Prints non-ASCII text to stdout (must not corrupt the protocol) and returns it."""
    print("stdout noise:", text)
    return {"text": text, "length": len(text)}


@tool("Path info")
def path_info(some_file: Path) -> Scalars:
    """Reports what the worker sees for a file path (spaces, non-ASCII, backslashes)."""
    return {
        "exists": some_file.exists(),
        "name": some_file.name,
        "size": some_file.stat().st_size,
        "as_posix": some_file.as_posix(),
    }


@tool("Plane mean")
def plane_mean(image: Annotated[Image, Axes("YX")]) -> Scalars:
    """Needs a single 2D plane: exercises the generic dimension check."""
    return {"mean": float(image.mean()), "shape": list(image.shape)}
