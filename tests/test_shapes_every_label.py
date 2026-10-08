"""F14: every label with at least `min_area` pixels appears exactly once, whatever the simplification.

Tolerances, stated once:
  * simplify = 0: the outline cuts each convex corner of the pixel-edge boundary at 45 degrees, so its area differs from the
    pixel count by at most 0.5 per boundary vertex pair; we allow `boundary_edges / 2 + 1` square pixels.
  * the outline rasterised back (pixel centres, even-odd) is the label mask exactly (simplify = 0), and always contains the
    centre of a single-pixel label.
"""

import importlib.util
import unittest

import _paths  # noqa: F401  (must come first)
import numpy as np
import roundtrip_harness as harness
import roundtrip_profiles  # noqa: F401
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from labconstrictor_tools import shapes

HAVE_SKIMAGE = importlib.util.find_spec("skimage") is not None
LABELS = hnp.arrays(
    np.uint8, hnp.array_shapes(min_dims=2, max_dims=2, min_side=1, max_side=12), elements=st.integers(0, 4)
)


def ring_area(ring):
    return 0.5 * abs(
        sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(len(ring) - 1))
    )


def feature_area(feature):
    g = feature["geometry"]
    polygons = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    return sum(ring_area(p[0]) - sum(ring_area(h) for h in p[1:]) for p in polygons)


def boundary_edges(mask):
    padded = np.pad(mask, 1).astype(np.int8)
    return int(sum(np.count_nonzero(np.diff(padded, axis=a)) for a in (0, 1)))


@unittest.skipUnless(HAVE_SKIMAGE, "scikit-image is needed for labels_to_shapes")
class EveryLabel(unittest.TestCase):
    @given(LABELS, st.sampled_from([0, 0.5, 1.0, 3.0]), st.integers(1, 6))
    def test_every_label_with_enough_pixels_appears_exactly_once(self, labels, simplify, min_area):
        found = shapes.labels_to_shapes(labels, simplify=simplify, min_area=min_area)["features"]
        wanted = sorted(int(v) for v in np.unique(labels) if v and (labels == v).sum() >= min_area)
        self.assertEqual(sorted(f["properties"]["label"] for f in found), wanted)
        for f in found:
            self.assertEqual(f["properties"]["area"], int((labels == f["properties"]["label"]).sum()))
            for polygon in (
                [f["geometry"]["coordinates"]]
                if f["geometry"]["type"] == "Polygon"
                else f["geometry"]["coordinates"]
            ):
                for ring in polygon:
                    self.assertGreaterEqual(len(ring), shapes.MIN_RING_POINTS)
                    self.assertEqual(ring[0], ring[-1])

    @given(LABELS)
    def test_unsimplified_areas_agree_with_pixel_counts_within_the_corner_cuts(self, labels):
        for f in shapes.labels_to_shapes(labels, simplify=0)["features"]:
            mask = labels == f["properties"]["label"]
            self.assertLessEqual(abs(feature_area(f) - mask.sum()), boundary_edges(mask) / 2 + 1)
            self.assertFalse((harness.rasterise(f, labels.shape) != mask).any())

    def test_a_collapsed_single_pixel_keeps_a_valid_outline_around_its_centre(self):
        labels = np.zeros((5, 5), np.uint8)
        labels[3, 1] = 1
        (feature,) = shapes.labels_to_shapes(labels)["features"]
        self.assertEqual(feature["geometry"]["type"], "Polygon")
        self.assertEqual(
            sorted(map(tuple, feature["geometry"]["coordinates"][0][:-1])),
            sorted([(1.0, 3.5), (0.5, 3.0), (1.0, 2.5), (1.5, 3.0)]),
        )
        self.assertEqual(feature["properties"], {"label": 1, "area": 1})

    def test_many_single_pixel_labels_all_get_a_feature(self):
        labels = np.zeros((9, 9), np.int32)
        labels[::2, ::2] = np.arange(1, 26).reshape(5, 5)
        found = shapes.labels_to_shapes(labels)["features"]
        self.assertEqual(sorted(f["properties"]["label"] for f in found), list(range(1, 26)))

    def test_a_collapsed_hole_is_kept_and_does_not_fill_the_label(self):
        labels = np.ones((5, 5), np.uint8)
        labels[2, 2] = 0
        (feature,) = shapes.labels_to_shapes(labels, simplify=1.0)["features"]
        self.assertEqual(len(feature["geometry"]["coordinates"]), 2)
        self.assertFalse(harness.rasterise(feature, labels.shape)[2, 2])


if __name__ == "__main__":
    unittest.main()
