"""Working with the region a person selected in the host (a parameter declared with `RegionOf("image")`).

    def segment(image, region: Annotated[Optional[Labels], RegionOf("image")] = None):
        box = bbox(region, image) if region is not None else (slice(None), slice(None))
        crop = image[box]          # work on the crop, then put the result back at box
"""

from __future__ import annotations

from typing import Any

from .types import ToolError


def bbox(mask: Any, image: Any = None) -> tuple[slice, slice]:
    """The (row slice, column slice) that encloses every non-zero pixel of the 2D `mask`.

    With `image` given, the mask must have the image's height and width. An empty mask is an error, not "the whole image":
    the person asked for a region and none was selected, so the tool says so.
    """
    import numpy as np

    array = np.asarray(mask)
    if array.ndim != 2:
        raise ToolError("bad_input", "the region must be a 2D label image, got %d dimensions" % array.ndim)
    if image is not None and tuple(array.shape) != tuple(np.asarray(image).shape[-2:]):
        raise ToolError(
            "bad_input", "the region (%d x %d) does not have the size of the image (%d x %d)" % (*array.shape, *np.asarray(image).shape[-2:])
        )
    rows, columns = np.nonzero(array)
    if rows.size == 0:
        raise ToolError("empty_region", "The selected region is empty: select an object, or untick 'use the selection'.")
    return slice(int(rows.min()), int(rows.max()) + 1), slice(int(columns.min()), int(columns.max()) + 1)
