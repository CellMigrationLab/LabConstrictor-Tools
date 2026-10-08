"""ShapesOut: the GeoJSON a tool may return, the readable refusals, and the labels_to_shapes helper (holes, parts, areas, scale)."""

import json
import math
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools.convert import _write_shapes
from labconstrictor_tools.types import ToolError

try:
    import numpy as np

    from labconstrictor_tools.shapes import _signed_area, labels_to_shapes

    HAVE_SKIMAGE = bool(__import__("skimage"))
except ImportError:  # the helper needs scikit-image (not a Tools dependency)
    HAVE_SKIMAGE = False


def write(value):
    folder = Path(tempfile.mkdtemp(prefix="lcshapes_"))
    result = _write_shapes("outlines", value, folder, {"apply_to": "image"})
    return result, json.loads(Path(result["path"]).read_text(encoding="utf-8"))


def area(feature):
    polygons = (
        [feature["geometry"]["coordinates"]]
        if feature["geometry"]["type"] == "Polygon"
        else feature["geometry"]["coordinates"]
    )
    return sum(abs(_signed_area(p[0])) - sum(abs(_signed_area(h)) for h in p[1:]) for p in polygons)


class Writing(unittest.TestCase):
    def test_polygons_given_as_y_x_become_geojson_x_y(self):
        result, collection = write(
            [
                [(0, 0), (0, 4), (3, 4), (3, 0)],
                {"polygon": [(10, 10), (10, 20), (20, 20)], "label": 7, "score": 0.5},
            ]
        )
        self.assertEqual((result["type"], result["n"], result["apply_to"]), ("shapes", 2, "image"))
        first = collection["features"][0]["geometry"]["coordinates"][0]
        self.assertEqual(first[1], [4.0, 0.0])  # (y=0, x=4) -> [x=4, y=0]
        self.assertEqual(first[0], first[-1])  # closed
        self.assertEqual(collection["features"][1]["properties"], {"label": 7, "score": 0.5})

    def test_a_feature_collection_passes_through(self):
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"a": 1},
                    "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [4, 0], [4, 4], [0, 0]]]},
                }
            ],
        }
        result, collection = write(fc)
        self.assertEqual(result["n"], 1)
        self.assertEqual(collection, fc)

    def test_an_empty_list_is_an_empty_collection(self):
        result, collection = write([])
        self.assertEqual((result["n"], collection["features"]), (0, []))

    def test_bad_input_is_refused_with_a_readable_message(self):
        cases = {
            "not a finite number": [[(0, 0), (0, float("nan")), (3, 4)]],
            "fewer than 3": [[(0, 0), (1, 1)]],
            "shape": [[1, 2, 3]],
            "key 'polygon'": [{"label": 1}],
            "FeatureCollection": {"type": "Feature"},
            "Point": {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 2]}}],
            },
            "must be a GeoJSON dict or a list": 5,
        }
        for word, value in cases.items():
            with self.subTest(word):
                with self.assertRaises(ToolError) as caught:
                    write(value)
                self.assertIn(word, str(caught.exception))

    def test_non_finite_geojson_coordinates_are_refused(self):
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [math.inf, 0], [4, 4], [0, 0]]]},
                }
            ],
        }
        with self.assertRaises(ToolError):
            write(fc)

    def test_unicode_properties_survive(self):
        _, collection = write([{"polygon": [(0, 0), (0, 4), (3, 4)], "name": "noyau µ→✓"}])
        self.assertEqual(collection["features"][0]["properties"]["name"], "noyau µ→✓")


@unittest.skipUnless(HAVE_SKIMAGE, "scikit-image is needed for labels_to_shapes")
class Helper(unittest.TestCase):
    def make(self):
        labels = np.zeros((30, 30), int)
        labels[2:8, 2:8] = 1  # a square
        labels[12:25, 12:25] = 2
        labels[16:20, 16:20] = 0  # a ring: a hole
        labels[2:5, 20:24] = 3
        labels[8:11, 20:24] = 3  # one label in two parts
        return labels

    def test_one_feature_per_label_with_holes_and_parts(self):
        fc = labels_to_shapes(self.make(), simplify=0)
        kinds = {f["properties"]["label"]: f["geometry"]["type"] for f in fc["features"]}
        self.assertEqual(kinds, {1: "Polygon", 2: "Polygon", 3: "MultiPolygon"})
        ring = next(f for f in fc["features"] if f["properties"]["label"] == 2)
        self.assertEqual(len(ring["geometry"]["coordinates"]), 2)  # outer boundary and one hole

    def test_the_area_matches_the_pixels_and_the_label_is_kept(self):
        for feature in labels_to_shapes(self.make(), simplify=0)["features"]:
            pixels = feature["properties"]["area"]
            self.assertLess(abs(area(feature) - pixels), 0.05 * pixels + 1, feature["properties"])

    def test_pixel_centres_are_at_integers(self):
        labels = np.zeros((10, 10), int)
        labels[3:6, 4:8] = 1  # rows 3..5, columns 4..7
        xs = [
            x
            for ring in labels_to_shapes(labels, simplify=0)["features"][0]["geometry"]["coordinates"]
            for x, _ in ring
        ]
        ys = [
            y
            for ring in labels_to_shapes(labels, simplify=0)["features"][0]["geometry"]["coordinates"]
            for _, y in ring
        ]
        self.assertAlmostEqual(
            min(xs), 3.5
        )  # the outline lies half a pixel outside the first pixel centre (4)
        self.assertAlmostEqual(max(xs), 7.5)
        self.assertAlmostEqual(min(ys), 2.5)
        self.assertAlmostEqual(max(ys), 5.5)

    def test_empty_and_wrong_inputs(self):
        self.assertEqual(labels_to_shapes(np.zeros((8, 8), int))["features"], [])
        with self.assertRaises(ToolError):
            labels_to_shapes(np.zeros((2, 8, 8), int))

    def test_min_area_skips_small_labels(self):
        fc = labels_to_shapes(self.make(), simplify=0, min_area=30)
        self.assertEqual(sorted(f["properties"]["label"] for f in fc["features"]), [1, 2])

    def test_many_labels_are_fast_enough(self):
        labels = np.zeros((400, 400), int)
        n = 0
        for r in range(0, 400, 4):
            for c in range(0, 400, 4):
                n += 1
                labels[r : r + 2, c : c + 2] = n
        fc = labels_to_shapes(labels)
        self.assertEqual(len(fc["features"]), n)

    def test_the_helper_output_is_accepted_as_a_shapes_result(self):
        result, collection = write(labels_to_shapes(self.make()))
        self.assertEqual(result["n"], 3)
        self.assertEqual(collection["type"], "FeatureCollection")


if __name__ == "__main__":
    unittest.main()
