"""#54: a returned GeoJSON dict is validated structurally (nesting, [x, y] positions, closed rings of at least 3 distinct vertices),
through `convert.build_results` as the worker calls it: a structurally invalid result is `bad_return` and no file is written, so no
successful result ever references invalid GeoJSON. Valid shapes (polygon, holes, multipolygon, no features) are written unchanged.
"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import convert
from labconstrictor_tools.types import ToolError

if TYPE_CHECKING:
    from typing import Any

SCHEMA = {"outputs": [{"name": "outlines", "type": "shapes"}]}
OUTER = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
HOLE = [[2, 2], [2, 4], [4, 4], [4, 2], [2, 2]]
TRIANGLE = [[20, 20], [25, 20], [20, 25], [20, 20]]


def collection(*geometries: "dict[str, Any]") -> "dict[str, Any]":
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"label": i + 1}, "geometry": g}
            for i, g in enumerate(geometries)
        ],
    }


def polygon(*rings: list[list[float]]) -> "dict[str, Any]":
    return {"type": "Polygon", "coordinates": list(rings)}


def run(value: "Any") -> "tuple[Any, Path]":
    folder = Path(tempfile.mkdtemp())
    try:
        return convert.build_results(SCHEMA, value, folder), folder
    except ToolError as error:
        return error, folder


class Valid(unittest.TestCase):
    def test_polygon_with_hole_multipolygon_and_empty_collection_roundtrip_unchanged(self) -> None:
        cases = {
            "polygon": collection(polygon(OUTER)),
            "polygon-with-hole": collection(polygon(OUTER, HOLE)),
            "multipolygon": collection({"type": "MultiPolygon", "coordinates": [[OUTER, HOLE], [TRIANGLE]]}),
            "empty-collection": collection(),
            "float-and-tuple-coordinates": collection(
                polygon([(0.5, 0.5), (3.5, 0.5), (0.5, 3.5), (0.5, 0.5)])
            ),
        }
        for name, value in cases.items():
            with self.subTest(name):
                results, _ = run(value)
                self.assertEqual(results[0]["n"], len(value["features"]))
                written = json.loads(Path(results[0]["path"]).read_text(encoding="utf-8"))
                self.assertEqual(written, json.loads(json.dumps(value)))


class Invalid(unittest.TestCase):
    def assertRefused(self, value: "Any", *words: str) -> None:
        got, folder = run(value)
        self.assertIsInstance(got, ToolError, "accepted: %r" % (value,))
        self.assertEqual(got.code, "bad_return")
        for word in words:
            self.assertIn(word, str(got))
        self.assertEqual(
            list(folder.iterdir()), [], "an invalid result must not leave a file the host could open"
        )

    def test_empty_and_missing_coordinates(self) -> None:
        self.assertRefused(collection(polygon()), "feature 0", "non-empty list of rings")
        self.assertRefused(
            collection({"type": "MultiPolygon", "coordinates": []}), "feature 0", "no coordinates"
        )
        self.assertRefused(collection({"type": "Polygon"}), "non-empty list of rings")
        self.assertRefused(collection({"type": "Polygon", "coordinates": "abc"}), "non-empty list of rings")
        self.assertRefused(collection(polygon([])), "feature 0", "ring 0", "at least 4")
        self.assertRefused(
            collection({"type": "MultiPolygon", "coordinates": [[]]}), "polygon 0", "non-empty list of rings"
        )

    def test_too_short_and_degenerate_rings_name_the_feature_and_ring(self) -> None:
        self.assertRefused(
            collection(polygon(OUTER), polygon([[0, 0], [1, 1], [0, 0]])), "feature 1", "ring 0", "at least 4"
        )
        self.assertRefused(
            collection(polygon(OUTER, [[1, 1], [2, 2], [3, 3]])), "feature 0", "ring 1", "at least 4"
        )
        self.assertRefused(
            collection(polygon([[0, 0], [1, 1], [1, 1], [0, 0]])), "ring 0", "fewer than 3 distinct"
        )
        self.assertRefused(collection(polygon([[0, 0], [0, 0], [0, 0], [0, 0]])), "fewer than 3 distinct")

    def test_open_rings(self) -> None:
        self.assertRefused(collection(polygon([[0, 0], [5, 0], [5, 5], [0, 5]])), "not closed")
        mp = {"type": "MultiPolygon", "coordinates": [[OUTER], [[[0, 0], [5, 0], [5, 5], [1, 1]]]]}
        self.assertRefused(collection(mp), "polygon 1", "ring 0", "not closed")

    def test_wrong_nesting(self) -> None:
        self.assertRefused(
            collection(polygon([1, 2])), "ring 0", "not an [x, y] pair"
        )  # a ring given as one position
        self.assertRefused(
            collection({"type": "Polygon", "coordinates": OUTER}), "ring 0", "not an [x, y] pair"
        )  # rings missing
        self.assertRefused(
            collection({"type": "MultiPolygon", "coordinates": [OUTER]}), "polygon 0", "ring 0"
        )  # a polygon missing
        self.assertRefused(collection({"type": "Polygon", "coordinates": [[[[0, 0]]]]}), "not an [x, y] pair")

    def test_wrong_position_shape(self) -> None:
        self.assertRefused(collection(polygon([[0], [1, 0], [1, 1], [0]])), "not an [x, y] pair")
        self.assertRefused(
            collection(polygon([[0, 0, 5], [1, 0, 5], [1, 1, 5], [0, 0, 5]])), "not an [x, y] pair"
        )
        self.assertRefused(
            collection(polygon([["a", "b"], [1, 0], [1, 1], ["a", "b"]])), "not an [x, y] pair"
        )
        self.assertRefused(
            collection(polygon([[True, False], [1, 0], [1, 1], [True, False]])), "not an [x, y] pair"
        )
        self.assertRefused(
            collection(polygon([[0, 0], [float("nan"), 0], [1, 1], [0, 0]])), "not a finite number"
        )
        self.assertRefused(
            collection(polygon([[0, 0], [float("inf"), 0], [1, 1], [0, 0]])), "not a finite number"
        )


if __name__ == "__main__":
    unittest.main()
