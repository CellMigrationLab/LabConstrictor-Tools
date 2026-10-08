"""Outlines from a label image, for a tool that returns `ShapesOut`.

    from labconstrictor_tools.shapes import labels_to_shapes
    return labels, labels_to_shapes(labels)

The result is a GeoJSON FeatureCollection (a dict) with one feature per label: a Polygon, or a MultiPolygon when the label has
several parts; holes are kept. Coordinates are [x, y] with pixel centres at integers, like every other coordinate the bridge uses.
Each feature has the properties `label` and `area` (pixels). Needs scikit-image and scipy, which an app that segments has;
Tools itself does not depend on them.
"""

from __future__ import annotations

from typing import Any

from .types import ToolError

CONTOUR_LEVEL = 0.5  # halfway between background (0) and label (1): the outline runs along pixel edges
DEFAULT_SIMPLIFY_PX = 0.5  # default for labels_to_shapes(simplify=...)
MIN_RING_POINTS = 4  # a closed ring needs 3 distinct vertices plus the repeated first one
MAX_LABELS_HINT = 50_000  # hosts show up to this many outlines and say how many were left out


def _signed_area(ring: list[list[float]]) -> float:
    x = [p[0] for p in ring]
    y = [p[1] for p in ring]
    return 0.5 * sum(x[i] * y[i + 1] - x[i + 1] * y[i] for i in range(len(ring) - 1))


def _inside(point: list[float], ring: list[list[float]]) -> bool:
    """Ray casting: is `point` inside the closed `ring` of [x, y]?"""
    px, py = point
    inside = False
    for i in range(len(ring) - 1):
        (x1, y1), (x2, y2) = ring[i], ring[i + 1]
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _rings_of(mask: Any, simplify: float) -> list[list[list[float]]]:
    """Closed rings of [x, y] around the True pixels of `mask` (outer boundaries and holes), centres at integers."""
    import numpy as np
    from skimage.measure import approximate_polygon, find_contours

    padded = np.pad(mask.astype(np.uint8), 1)
    rings: list[list[list[float]]] = []
    for contour in find_contours(padded, CONTOUR_LEVEL):
        if simplify and simplify > 0:
            simplified = approximate_polygon(contour, simplify)
            # a ring that simplification collapses (a single pixel, a 1x3 bar) keeps its un-simplified outline: never drop a label
            contour = simplified if len(simplified) >= MIN_RING_POINTS else contour
        ring = [
            [float(c) - 1.0, float(r) - 1.0] for r, c in contour
        ]  # undo the padding; (row, col) -> [x, y]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        rings.append(ring)
    return rings


def _polygons(rings: list[list[list[float]]]) -> list[list[list[list[float]]]]:
    """Group rings into polygons: a ring turning the way the biggest one does is an outer boundary, the others are holes of the
    outer boundary that contains them."""
    if not rings:
        return []
    biggest = max(rings, key=lambda r: abs(_signed_area(r)))
    outer_sign = 1 if _signed_area(biggest) > 0 else -1
    outers = [r for r in rings if (_signed_area(r) > 0) == (outer_sign > 0)]
    holes = [r for r in rings if (_signed_area(r) > 0) != (outer_sign > 0)]
    polygons: list[list[list[list[float]]]] = [[outer] for outer in outers]
    for hole in holes:
        owners = [i for i, outer in enumerate(outers) if _inside(hole[0], outer)]
        if owners:  # the smallest outer boundary that contains the hole
            polygons[min(owners, key=lambda i: abs(_signed_area(outers[i])))].append(hole)
    return polygons


def labels_to_shapes(labels: Any, simplify: float = DEFAULT_SIMPLIFY_PX, min_area: int = 1) -> dict[str, Any]:
    """GeoJSON FeatureCollection of the outlines of a 2D label image.

    `simplify` is the largest distance in pixels an outline may move when it is simplified (0 keeps every pixel corner);
    `min_area` skips labels with fewer pixels. Every label with at least `min_area` pixels gets exactly one feature: when
    simplification would leave a ring with fewer than 3 vertices (a single pixel, a 1x3 bar), that ring keeps its
    UN-simplified outline instead, so no label is ever dropped silently. For a single pixel at (y, x) this is the diamond
    with vertices (x, y +- 0.5) and (x +- 0.5, y), a valid 4-vertex polygon around the pixel centre.
    """
    import numpy as np
    from scipy import ndimage

    array = np.asarray(labels)
    if array.ndim != 2:
        raise ToolError(
            "bad_input", "labels_to_shapes needs a 2D label image, got %d dimensions" % array.ndim
        )
    features = []
    for index, region in enumerate(ndimage.find_objects(array.astype(np.int64, copy=False)), start=1):
        if region is None:
            continue
        crop = array[region] == index
        area = int(crop.sum())
        if area < min_area:
            continue
        polygons = _polygons(_rings_of(crop, simplify))
        if (
            not polygons
        ):  # cannot happen (every non-empty mask has a contour of >= 4 points); never skip silently
            raise ToolError("bad_return", "label %d has %d pixels but no outline" % (index, area))
        dy, dx = region[0].start, region[1].start
        shifted = [[[[x + dx, y + dy] for x, y in ring] for ring in polygon] for polygon in polygons]
        geometry = (
            {"type": "Polygon", "coordinates": shifted[0]}
            if len(shifted) == 1
            else {"type": "MultiPolygon", "coordinates": shifted}
        )
        features.append(
            {"type": "Feature", "properties": {"label": index, "area": area}, "geometry": geometry}
        )
    return {"type": "FeatureCollection", "features": features}
