"""A small app that uses every interaction hint once: copy what you need.

    labconstrictor-tools check --module labconstrictor_tools.examples.interactions
    labconstrictor-tools run   interactions ...        (after `labconstrictor-tools register`)

A "pick the odd one out" game: `start` makes a round, `answer` takes the guess from a dropdown filled by `list_shapes`.
numpy and pandas are only imported inside the functions: hosts import this file just to list the tools.
"""

from typing import Annotated, Literal, Optional

from labconstrictor_tools import (
    ApplyTo,
    Axes,
    ChoicesFrom,
    ClearAfterRun,
    Collapsed,
    Description,
    Group,
    Image,
    ImageOut,
    Max,
    MessageOut,
    Min,
    Name,
    PickChannel,
    PointsOut,
    Widget,
    Replace,
    Scalars,
    TableOut,
    ToolError,
    tool,
)

SHAPES = ["square", "bar", "dot"]


@tool("List the shapes")
def list_shapes() -> Scalars:
    """The options of the `guess` dropdown. A ChoicesFrom source returns Scalars with a list (here under `choices`)."""
    return {"choices": SHAPES}


@tool("Show a shape")
def show_shape(
    shape: Annotated[
        Optional[str],
        Group("Play"),
        ChoicesFrom("list_shapes"),  # a dropdown where the host can, a text field where it cannot: accept any string
        ClearAfterRun(),  # Napari empties it after a successful run, so a stale answer is never sent twice
        Description("Pick a shape to draw; leave unset to draw the default one"),
    ] = None,
    size: Annotated[int, Group("Options"), Collapsed(), Description("Size in pixels (this group starts folded)")] = 32,
) -> tuple[
    Annotated[ImageOut, Name("picture"), Replace()],  # each run replaces the previous picture (one layer / window)
    Annotated[PointsOut, Name("corners"), Replace()],  # y, x (+ properties) -> points layer / point ROIs / point annotations
    Annotated[MessageOut, Name("note")],  # a short message for the user
]:
    """Draw a shape, mark its corners and say what was drawn."""
    import numpy as np

    shape = shape or SHAPES[0]
    if shape not in SHAPES:
        raise ToolError("unknown_shape", "Unknown shape '%s'. Choose one of: %s." % (shape, ", ".join(SHAPES)))
    image = np.zeros((size, size), np.uint8)
    q = size // 4
    if shape == "square":
        image[q : size - q, q : size - q] = 255
    elif shape == "bar":
        image[size // 2 - 2 : size // 2 + 2, q : size - q] = 255
    else:
        image[size // 2 - 2 : size // 2 + 2, size // 2 - 2 : size // 2 + 2] = 255
    ys, xs = np.nonzero(image)
    corners = [{"y": float(ys.min()), "x": float(xs.min()), "corner": "top-left"}, {"y": float(ys.max()), "x": float(xs.max()), "corner": "bottom-right"}]
    return image, corners, "Drew a **%s** of %d px." % (shape, size)


@tool("Find bright spots")
def find_bright_spots(
    image: Annotated[Image, Axes("YX"), Description("The image to search")],
    threshold: Annotated[float, Min(0), Max(1), Widget("slider"), Description("Fraction of the maximum above which a pixel counts as a spot")] = 0.8,
    look_for: Annotated[Literal["bright", "dark"], Widget("radio"), Description("Mark bright spots, or dark ones (the image is inverted first)")] = "bright",
) -> tuple[
    Annotated[PointsOut, Name("spots"), ApplyTo("image"), Replace()],  # ApplyTo: the pixels these y, x belong to
    Annotated[MessageOut, Name("summary")],
]:
    """Mark the local maxima above a threshold: a minimal example of returning objects found in an image."""
    import numpy as np
    from scipy.ndimage import maximum_filter

    if look_for == "dark":
        image = image.max() - image
    peak = float(image.max())
    if peak <= 0:
        raise ToolError("no_result", "The image is empty (its maximum is 0): nothing to find.")
    is_peak = (image == maximum_filter(image, size=5)) & (image >= threshold * peak)
    ys, xs = np.nonzero(is_peak)
    if len(ys) == 0:
        raise ToolError("no_result", "No spot above %.0f%% of the maximum." % (100 * threshold))
    return [{"y": float(y), "x": float(x), "intensity": float(image[y, x])} for y, x in zip(ys, xs)], "Found **%d** spot(s)." % len(ys)


@tool("Mean of a channel")
def channel_mean(
    image: Annotated[Image, Axes("YX"), PickChannel(), Description("A multi-channel image: choose the channel in the host")],
) -> Scalars:
    """A 2D tool that works on one channel of a multi-channel image: with PickChannel the host sends only the chosen channel."""
    return {"mean": round(float(image.mean()), 4), "shape": "%d x %d" % image.shape}


@tool("Check this installation")
def check_installation() -> tuple[Annotated[MessageOut, Name("readout")], Annotated[TableOut, Name("details")]]:
    """What a person can run to see whether the machine, the worker and the GPU libraries are in order (the same three lines work in any app)."""
    from labconstrictor_tools import diagnostics

    checks = diagnostics.run_checks(benchmark=False)
    return diagnostics.summary(checks), diagnostics.rows(checks)
