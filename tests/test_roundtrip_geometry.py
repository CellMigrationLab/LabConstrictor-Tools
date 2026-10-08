"""Metamorphic checks of the geometry the bridge hands to hosts: outlines of labels, the region box, and the pixel-centre
convention. A transformed input must give the matching transformed output; a swapped (y, x), a lost half pixel or a dropped hole
cannot hide. The oracle is numpy plus the even-odd rasteriser of roundtrip_harness.py (not the production point-in-polygon).

Tolerances, stated once:
  * simplify = 0 keeps every pixel corner: the outline rasterised back (pixel centres at integers, even-odd rule) is the label
    mask EXACTLY;
  * simplify = s > 0 moves the outline by at most s pixels: the mask may differ in at most ceil(2 * s * P) + 4 pixels, P being the
    number of pixel edges on the boundary of the label (a band 2 s wide around a path of length P).
"""

import importlib.util
import json
import math
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
import numpy as np
import roundtrip_harness as harness
import roundtrip_profiles  # noqa: F401  (registers and loads the hypothesis profile)
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp
from roundtrip_known_failures import known_failure

from labconstrictor_tools import region, shapes
from labconstrictor_tools.types import ToolError

HAVE_SKIMAGE = importlib.util.find_spec("skimage") is not None

LABELS = hnp.arrays(
    np.uint8, hnp.array_shapes(min_dims=2, max_dims=2, min_side=1, max_side=12), elements=st.integers(0, 3)
)
BLOBS = st.lists(
    st.tuples(
        st.integers(1, 3), st.integers(0, 14), st.integers(0, 14), st.integers(1, 6), st.integers(1, 6)
    ),
    min_size=1,
    max_size=4,
).map(lambda boxes: _paint(boxes))


def _paint(boxes):
    image = np.zeros((20, 20), np.uint8)
    for label, y, x, h, w in boxes:
        image[y : y + h, x : x + w] = label
    return image


def boundary_edges(mask):
    """P: the number of pixel edges between a pixel of the mask and a pixel outside it (or the image edge)."""
    padded = np.pad(mask, 1).astype(np.int8)
    return int(sum(np.count_nonzero(np.diff(padded, axis=axis)) for axis in (0, 1)))


def features_by_label(collection):
    return {f["properties"]["label"]: f for f in collection["features"]}


def all_vertices(feature):
    geometry = feature["geometry"]
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    return {(x, y) for polygon in polygons for ring in polygon for x, y in ring}


def moved(coordinates, dx, dy):
    if isinstance(coordinates[0], (int, float)):
        return [coordinates[0] + dx, coordinates[1] + dy]
    return [moved(c, dx, dy) for c in coordinates]


def mapped(coordinates, function):
    if isinstance(coordinates[0], (int, float)):
        return list(function(*coordinates))
    return [mapped(c, function) for c in coordinates]


@unittest.skipUnless(HAVE_SKIMAGE, "scikit-image is needed for labels_to_shapes")
class Outlines(unittest.TestCase):
    @given(st.one_of(LABELS, BLOBS))
    def test_rasterised_back_equals_the_labels_exactly(self, labels):
        collection = shapes.labels_to_shapes(labels, simplify=0)
        found = features_by_label(collection)
        self.assertEqual(sorted(found), sorted(int(v) for v in np.unique(labels) if v))
        for label, feature in found.items():
            mask = labels == label
            self.assertTrue(
                np.array_equal(harness.rasterise(feature, labels.shape), mask), "label %d" % label
            )
            self.assertEqual(feature["properties"]["area"], int(mask.sum()))

    @given(BLOBS, st.sampled_from([0.25, 0.5, 1.0]))
    def test_simplified_outlines_stay_within_the_stated_tolerance(self, labels, simplify):
        found = features_by_label(shapes.labels_to_shapes(labels, simplify=simplify))
        for label, feature in found.items():
            mask = labels == label
            wrong = int(np.count_nonzero(harness.rasterise(feature, labels.shape) != mask))
            self.assertLessEqual(
                wrong, math.ceil(2 * simplify * boundary_edges(mask)) + 4, "label %d" % label
            )

    @given(st.one_of(LABELS, BLOBS), st.integers(0, 7), st.integers(0, 7), st.sampled_from([0, 0.5]))
    def test_translating_the_labels_translates_the_outlines(self, labels, dy, dx, simplify):
        shifted = np.pad(labels, ((dy, 0), (dx, 0)))
        before = features_by_label(shapes.labels_to_shapes(labels, simplify=simplify))
        after = features_by_label(shapes.labels_to_shapes(shifted, simplify=simplify))
        self.assertEqual(sorted(before), sorted(after))
        for label, feature in before.items():
            self.assertEqual(
                after[label]["geometry"]["coordinates"], moved(feature["geometry"]["coordinates"], dx, dy)
            )

    @given(st.one_of(LABELS, BLOBS))
    def test_transposing_the_labels_swaps_x_and_y(self, labels):
        before = features_by_label(shapes.labels_to_shapes(labels, simplify=0))
        after = features_by_label(shapes.labels_to_shapes(labels.T, simplify=0))
        self.assertEqual(sorted(before), sorted(after))
        for label, feature in before.items():
            self.assertEqual(
                {(y, x) for x, y in all_vertices(feature)}, all_vertices(after[label]), "label %d" % label
            )
            swapped = {
                "geometry": {
                    "type": feature["geometry"]["type"],
                    "coordinates": mapped(feature["geometry"]["coordinates"], lambda x, y: (y, x)),
                }
            }
            self.assertTrue(np.array_equal(harness.rasterise(swapped, labels.T.shape), labels.T == label))

    @given(st.one_of(LABELS, BLOBS))
    def test_flipping_the_labels_mirrors_the_outlines(self, labels):
        width = labels.shape[1]
        flipped = labels[:, ::-1]
        before = features_by_label(shapes.labels_to_shapes(labels, simplify=0))
        after = features_by_label(shapes.labels_to_shapes(flipped, simplify=0))
        self.assertEqual(sorted(before), sorted(after))
        for label, feature in before.items():
            self.assertEqual(
                {(width - 1 - x, y) for x, y in all_vertices(feature)}, all_vertices(after[label])
            )

    @given(st.integers(1, 6), st.integers(1, 6), st.integers(0, 5), st.integers(0, 5))
    def test_pixel_centres_are_at_integers_and_outlines_run_along_pixel_edges(
        self, height, width, row, column
    ):
        labels = np.zeros((row + height + 1, column + width + 1), np.uint8)
        labels[row : row + height, column : column + width] = 1
        feature = features_by_label(shapes.labels_to_shapes(labels, simplify=0))[1]
        xs = [x for x, _ in all_vertices(feature)]
        ys = [y for _, y in all_vertices(feature)]
        self.assertEqual((min(xs), max(xs)), (column - 0.5, column + width - 0.5))
        self.assertEqual((min(ys), max(ys)), (row - 0.5, row + height - 0.5))
        for r in range(labels.shape[0]):
            for c in range(labels.shape[1]):
                inside = harness.rasterise(feature, labels.shape)[r, c]
                self.assertEqual(
                    bool(inside), bool(labels[r, c]), "pixel centre (row %d, column %d)" % (r, c)
                )

    def test_a_single_pixel_is_a_diamond_around_its_centre(self):
        labels = np.zeros((5, 7), np.uint8)
        labels[2, 3] = 1  # row 2, column 3
        feature = features_by_label(shapes.labels_to_shapes(labels, simplify=0))[1]
        self.assertEqual(all_vertices(feature), {(3.0, 1.5), (3.0, 2.5), (2.5, 2.0), (3.5, 2.0)})

    def test_a_label_with_a_hole_keeps_the_hole(self):
        labels = np.zeros((9, 9), np.uint8)
        labels[1:8, 1:8] = 1
        labels[3:6, 3:6] = 0
        feature = features_by_label(shapes.labels_to_shapes(labels, simplify=0))[1]
        self.assertEqual(feature["geometry"]["type"], "Polygon")
        self.assertEqual(len(feature["geometry"]["coordinates"]), 2, "the outer ring and one hole")
        raster = harness.rasterise(feature, labels.shape)
        self.assertFalse(raster[4, 4], "the centre of the hole must stay outside")
        self.assertEqual(int(raster.sum()), 49 - 9)
        self.assertEqual(feature["properties"]["area"], 40)

    def test_parts_make_a_multipolygon_and_each_part_keeps_its_own_hole(self):
        labels = np.zeros((9, 20), np.uint8)
        labels[1:8, 1:8] = 1
        labels[3:6, 3:6] = 0
        labels[1:8, 11:18] = 1
        labels[3:6, 13:16] = 0
        feature = features_by_label(shapes.labels_to_shapes(labels, simplify=0))[1]
        self.assertEqual(feature["geometry"]["type"], "MultiPolygon")
        self.assertEqual(sorted(len(polygon) for polygon in feature["geometry"]["coordinates"]), [2, 2])
        self.assertTrue(np.array_equal(harness.rasterise(feature, labels.shape), labels == 1))

    def test_an_island_inside_a_hole_is_its_own_label_and_does_not_fill_the_hole(self):
        labels = np.zeros((9, 9), np.uint8)
        labels[1:8, 1:8] = 1
        labels[3:6, 3:6] = 0
        labels[4, 4] = 2
        found = features_by_label(shapes.labels_to_shapes(labels, simplify=0))
        self.assertFalse(harness.rasterise(found[1], labels.shape)[4, 4])
        self.assertTrue(harness.rasterise(found[2], labels.shape)[4, 4])

    @known_failure("test:test_roundtrip_geometry.Outlines.test_default_simplification_never_drops_a_label")
    def test_default_simplification_never_drops_a_label(self):
        for height, width in ((1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1)):
            labels = np.zeros((7, 7), np.uint8)
            labels[2 : 2 + height, 2 : 2 + width] = 1
            for simplify in (shapes.DEFAULT_SIMPLIFY_PX, 1.0):
                with self.subTest(size=(height, width), simplify=simplify):
                    found = shapes.labels_to_shapes(labels, simplify=simplify, min_area=1)["features"]
                    self.assertEqual(
                        [f["properties"]["label"] for f in found],
                        [1],
                        "an object of %d pixels vanished" % (height * width),
                    )

    @given(LABELS, st.integers(1, 40))
    def test_min_area_only_removes_labels_and_never_changes_the_rest(self, labels, area):
        everything = features_by_label(shapes.labels_to_shapes(labels, simplify=0, min_area=1))
        some = features_by_label(shapes.labels_to_shapes(labels, simplify=0, min_area=area))
        areas = {int(v): int((labels == v).sum()) for v in np.unique(labels) if v}
        self.assertEqual(sorted(some), sorted(label for label, a in areas.items() if a >= area))
        for label, feature in some.items():
            self.assertEqual(feature, everything[label])

    @given(LABELS)
    def test_min_area_is_monotone(self, labels):
        counts = [
            len(shapes.labels_to_shapes(labels, simplify=0, min_area=a)["features"]) for a in range(1, 30)
        ]
        self.assertEqual(counts, sorted(counts, reverse=True))
        sets = [
            set(features_by_label(shapes.labels_to_shapes(labels, simplify=0, min_area=a)))
            for a in (1, 3, 9, 27)
        ]
        for bigger, smaller in zip(sets[1:], sets[:-1]):
            self.assertTrue(bigger <= smaller)

    def test_the_same_checks_through_a_worker(self):
        """The host's view: the GeoJSON file a real worker writes obeys the same translation and transposition rules."""
        session = harness.Session()
        try:
            labels = np.zeros((9, 11), np.uint8)
            labels[1:6, 2:5] = 1
            labels[2:4, 3:4] = 0
            labels[7, 9] = 2
            runs = {}
            for name, array in (
                ("plain", labels),
                ("shifted", np.pad(labels, ((3, 0), (5, 0)))),
                ("transposed", labels.T),
            ):
                folder = session.case_dir()
                wire, _ = session.materialise(_case(array), folder)
                task = (
                    session.worker()
                    .task("outline_labels", {**wire, "simplify": 0.0, "_job_dir": str(folder / "out")})
                    .wait(60)
                )
                self.assertEqual(task.status, "COMPLETE", task.error)
                path = Path(task.outputs["results"][0]["path"])
                runs[name] = features_by_label(json.loads(path.read_text(encoding="utf-8")))
            for label, feature in runs["plain"].items():
                self.assertEqual(
                    runs["shifted"][label]["geometry"]["coordinates"],
                    moved(feature["geometry"]["coordinates"], 5, 3),
                )
                self.assertEqual(
                    {(y, x) for x, y in all_vertices(feature)}, all_vertices(runs["transposed"][label])
                )
        finally:
            session.close()


def _case(array):
    from roundtrip_cases import Case, Expect

    return Case("geometry", "outline_labels", {"labels": array}, Expect())


class RegionBox(unittest.TestCase):
    @given(
        hnp.arrays(
            np.uint8,
            hnp.array_shapes(min_dims=2, max_dims=2, min_side=1, max_side=12),
            elements=st.integers(0, 2),
        )
    )
    def test_the_box_of_a_mask_is_numpys_box(self, mask):
        if not mask.any():
            with self.assertRaises(ToolError) as caught:
                region.bbox(mask)
            self.assertEqual(caught.exception.code, "empty_region")
            return
        rows, columns = np.nonzero(mask)
        box = region.bbox(mask)
        self.assertEqual(
            box,
            (slice(int(rows.min()), int(rows.max()) + 1), slice(int(columns.min()), int(columns.max()) + 1)),
        )
        crop = mask[box]
        self.assertTrue(
            crop[0].any() and crop[-1].any() and crop[:, 0].any() and crop[:, -1].any(), "the box is tight"
        )
        self.assertEqual(
            int(crop.astype(bool).sum()), int(mask.astype(bool).sum()), "nothing outside the box"
        )

    @given(st.integers(1, 9), st.integers(1, 9), st.integers(0, 3), st.integers(0, 3))
    def test_transposing_the_mask_swaps_the_rows_and_columns_of_the_box(self, height, width, row, column):
        mask = np.zeros((row + height + 2, column + width + 2), np.uint8)
        mask[row : row + height, column : column + width] = 1
        rows, columns = region.bbox(mask)
        t_rows, t_columns = region.bbox(mask.T)
        self.assertEqual((rows, columns), (t_columns, t_rows))

    @given(st.integers(0, 4), st.integers(0, 4))
    def test_translating_the_mask_translates_the_box(self, dy, dx):
        mask = np.zeros((6, 7), np.uint8)
        mask[1:4, 2:6] = 1
        shifted = np.pad(mask, ((dy, 0), (dx, 0)))
        rows, columns = region.bbox(mask)
        s_rows, s_columns = region.bbox(shifted)
        self.assertEqual((s_rows.start - rows.start, s_columns.start - columns.start), (dy, dx))
        self.assertEqual(
            (s_rows.stop - s_rows.start, s_columns.stop - s_columns.start),
            (rows.stop - rows.start, columns.stop - columns.start),
        )

    def test_the_messages_a_person_reads_say_what_is_wrong_in_numbers(self):
        with self.assertRaises(ToolError) as caught:
            region.bbox(np.zeros((2, 3, 3), np.uint8))
        self.assertEqual(
            (caught.exception.code, caught.exception.message),
            ("bad_input", "the region must be a 2D label image, got 3 dimensions"),
        )
        with self.assertRaises(ToolError) as caught:
            region.bbox(np.ones((4, 5), np.uint8), np.zeros((2, 6, 7)))
        self.assertEqual(
            (caught.exception.code, caught.exception.message),
            ("bad_input", "the region (4 x 5) does not have the size of the image (6 x 7)"),
        )
        with self.assertRaises(ToolError) as caught:
            region.bbox(np.zeros((2, 2), np.uint8))
        self.assertEqual(caught.exception.code, "empty_region")
        self.assertEqual(
            caught.exception.message,
            "The selected region is empty: select an object, or untick 'use the selection'.",
        )

    def test_a_mask_the_size_of_a_3d_image_plane_is_accepted_and_other_sizes_are_refused(self):
        mask = np.zeros((7, 9), np.uint8)
        mask[2, 3] = 1
        self.assertEqual(region.bbox(mask, np.zeros((4, 7, 9))), (slice(2, 3), slice(3, 4)))
        with self.assertRaises(ToolError) as caught:
            region.bbox(mask, np.zeros((9, 7)))  # the transposed size: a swapped (height, width) is caught
        self.assertEqual(caught.exception.code, "bad_input")


def tearDownModule():
    """Release what this module's tests left to the garbage collector now, so that a ResourceWarning for an unclosed pipe is
    raised here and not in whichever test happens to run next (some older tests count ResourceWarnings)."""
    import gc

    gc.collect()


if __name__ == "__main__":
    unittest.main()
