"""Result images with known axes: an ImageJ hyperstack when the axes are in ImageJ order, never a reordered array.

A tool states the axes of an image result with `Axes(...)` on the output or, when they depend on its input, by returning
`WithAxes(array, axes)`. Axes that are a subsequence of T Z C Y X (ending in Y X) and a pixel type ImageJ stores give an ImageJ
hyperstack TIFF, so Fiji opens a time-lapse with its time points instead of one long stack. Reading the file back gives the same
array, so napari, notebooks and the case runner see what they saw before. Anything else is written as before (feature
`result_axes_v1`).
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any

import numpy as np
import tifffile

from labconstrictor_tools import ToolError, WithAxes, convert, features


def write(value: Any, axes: str | None = None) -> tuple[dict[str, Any], Path]:
    out: dict[str, Any] = {"type": "image", "name": "result"}
    if axes:
        out["axes"] = axes
    result = convert._write_one(out, value, Path(tempfile.mkdtemp()))  # type: ignore[arg-type]
    return dict(result), Path(result["path"])


def imagej(path: Path) -> dict[str, Any] | None:
    with tifffile.TiffFile(path) as tif:
        return tif.imagej_metadata


def array(shape: tuple[int, ...], dtype: Any = np.float32) -> Any:
    return (np.arange(int(np.prod(shape))) % 251).astype(dtype).reshape(shape)


class ImageJHyperstacks(unittest.TestCase):
    CASES = (  # axes, shape, (frames, slices, channels) ImageJ records
        ("TYX", (5, 8, 10), (5, None, None)),
        ("TZYX", (4, 3, 8, 10), (4, 3, None)),
        ("ZCYX", (3, 2, 8, 10), (None, 3, 2)),
        ("CYX", (3, 8, 10), (None, None, 3)),
        ("TZCYX", (2, 3, 2, 8, 10), (2, 3, 2)),
    )

    def test_returned_axes_give_a_hyperstack_and_the_same_array(self) -> None:
        for axes, shape, (frames, slices, channels) in self.CASES:
            for dtype in (np.uint8, np.uint16, np.int16, np.float32):
                data = array(shape, dtype)
                with self.subTest(axes=axes, dtype=np.dtype(dtype).name):
                    result, path = write(WithAxes(data, axes))
                    meta = imagej(path)
                    assert meta is not None
                    self.assertEqual(
                        (meta.get("frames"), meta.get("slices"), meta.get("channels")),
                        (frames, slices, channels),
                    )
                    self.assertTrue(meta.get("hyperstack"))
                    back = tifffile.imread(path)
                    self.assertEqual(back.dtype, data.dtype)
                    np.testing.assert_array_equal(back, data)
                    self.assertEqual(result["axes"], axes)

    def test_declared_axes_in_imagej_order_give_a_hyperstack(self) -> None:
        result, path = write(array((4, 3, 8, 10)), axes="TZYX")
        meta = imagej(path)
        assert meta is not None
        self.assertEqual((meta.get("frames"), meta.get("slices")), (4, 3))
        self.assertEqual(result["axes"], "TZYX")

    def test_three_channels_with_axes_open_in_fiji_too(self) -> None:
        """The case of #163, now with axes: a hyperstack of 3 channels (Fiji opens it), the same array back."""
        data = array((3, 8, 10))
        _, path = write(WithAxes(data, "CYX"))
        np.testing.assert_array_equal(tifffile.imread(path), data)
        meta = imagej(path)
        assert meta is not None
        self.assertEqual(meta.get("channels"), 3)


class WrittenAsBefore(unittest.TestCase):
    def test_unknown_axes_are_never_guessed_into_a_hyperstack(self) -> None:
        """A 4D result without axes is labelled CZYX by default; that guess must not decide how Fiji shows it."""
        data = array((4, 3, 8, 10))
        result, path = write(data)
        self.assertIsNone(imagej(path))
        self.assertEqual(result["axes"], "CZYX")
        np.testing.assert_array_equal(tifffile.imread(path), data)

    def test_axes_not_in_imagej_order_are_kept_and_the_array_is_not_reordered(self) -> None:
        for axes, shape in (
            ("CZYX", (2, 3, 8, 10)),
            ("ZTYX", (3, 4, 8, 10)),
            ("YXC", (8, 10, 3)),
            ("YXS", (8, 10, 3)),
        ):
            data = array(shape, np.uint8 if axes == "YXS" else np.float32)
            with self.subTest(axes=axes):
                result, path = write(WithAxes(data, axes))
                self.assertIsNone(imagej(path))
                np.testing.assert_array_equal(tifffile.imread(path), data)
                self.assertEqual(result["axes"], axes)

    def test_a_pixel_type_imagej_cannot_store_is_written_as_before(self) -> None:
        """portable_dtype leaves a big-endian 16-bit array as it is; tifffile cannot write it in ImageJ mode."""
        data = array((4, 8, 10), ">u2")
        _, path = write(WithAxes(data, "TYX"))
        self.assertIsNone(imagej(path))
        np.testing.assert_array_equal(tifffile.imread(path), data)

    def test_a_dimension_of_size_1_is_never_dropped(self) -> None:
        """ImageJ cannot record a T, Z or C of size 1: such a result is written as before and reads back with every dimension,
        also when only Axes is declared (found by an independent review)."""
        cases = (
            ("TZYX", (3, 1, 8, 9), True),
            ("TZYX", (1, 4, 8, 9), True),
            ("TYX", (1, 8, 9), True),
            ("ZYX", (1, 8, 9), False),
            ("ZCYX", (4, 1, 8, 9), True),
            ("TZYX", (3, 4, 8, 1), True),
        )
        for axes, shape, returned in cases:
            data = array(shape, np.uint8)
            with self.subTest(axes=axes, shape=shape, returned=returned):
                result, path = write(WithAxes(data, axes)) if returned else write(data, axes=axes)
                self.assertIsNone(imagej(path))
                back = tifffile.imread(path)
                self.assertEqual(back.shape, data.shape)
                np.testing.assert_array_equal(back, data)
                self.assertEqual(result["axes"], axes)

    def test_a_result_of_4_gib_or_more_is_written_as_before(self) -> None:
        """An ImageJ TIFF is never a BigTIFF: above the limit the result is written as before (the limit is lowered here)."""
        data = array((4, 8, 10), np.uint16)
        limit = convert.IMAGEJ_MAX_BYTES
        convert.IMAGEJ_MAX_BYTES = data.nbytes
        try:
            _, path = write(WithAxes(data, "TYX"))
        finally:
            convert.IMAGEJ_MAX_BYTES = limit
        self.assertIsNone(imagej(path))
        np.testing.assert_array_equal(tifffile.imread(path), data)

    def test_a_2d_result_is_written_as_before(self) -> None:
        _, path = write(WithAxes(array((8, 10)), "YX"))
        self.assertIsNone(imagej(path))


class OtherResults(unittest.TestCase):
    def test_a_label_result_with_axes_is_a_hyperstack_too(self) -> None:
        data = array((3, 4, 8, 10), np.uint16)
        out = {"type": "labels", "name": "masks"}
        result = convert._write_one(out, WithAxes(data, "TZYX"), Path(tempfile.mkdtemp()))  # type: ignore[arg-type]
        meta = imagej(Path(result["path"]))
        assert meta is not None
        self.assertEqual((meta.get("frames"), meta.get("slices")), (3, 4))
        np.testing.assert_array_equal(tifffile.imread(result["path"]), data)

    def test_booleans_become_0_and_1_bytes_in_a_hyperstack(self) -> None:
        data = array((3, 4, 8, 10), np.uint8) % 2 == 0
        _, path = write(WithAxes(data, "TZYX"))
        self.assertIsNotNone(imagej(path))
        np.testing.assert_array_equal(tifffile.imread(path), data.astype(np.uint8))

    def test_a_declared_axes_result_reads_back_the_same(self) -> None:
        for axes, shape in (("ZYX", (4, 8, 10)), ("ZYX", (4, 8, 3)), ("CYX", (3, 8, 10))):
            data = array(shape, np.uint8)
            with self.subTest(axes=axes, shape=shape):
                _, path = write(data, axes=axes)
                self.assertIsNotNone(imagej(path))
                back = tifffile.imread(path)
                self.assertEqual(back.shape, data.shape)
                np.testing.assert_array_equal(back, data)


class Refusals(unittest.TestCase):
    def refused(self, value: Any, axes: str | None = None) -> str:
        with self.assertRaises(ToolError) as caught:
            write(value, axes)
        self.assertEqual(caught.exception.code, "bad_return")
        return caught.exception.message

    def test_axes_that_do_not_fit_the_array(self) -> None:
        self.assertIn("returned with axes TZYX (4D)", self.refused(WithAxes(array((5, 8, 10)), "TZYX")))

    def test_letters_that_are_not_axes_or_repeated(self) -> None:
        for axes in ("TQX", "TTYX", "", 3):
            with self.subTest(axes=axes):
                self.assertIn("was returned with axes", self.refused(WithAxes(array((5, 8, 10)), axes)))  # type: ignore[arg-type]

    def test_returned_axes_must_agree_with_the_declared_ones(self) -> None:
        self.assertIn(
            "is declared TZYX but was returned with axes ZCYX",
            self.refused(WithAxes(array((4, 3, 8, 10)), "ZCYX"), "TZYX"),
        )

    def test_the_wrapped_value_is_still_checked(self) -> None:
        self.assertIn("array of numbers", self.refused(WithAxes("not an image", "YX")))


class FeatureId(unittest.TestCase):
    def test_the_feature_is_listed_and_documented(self) -> None:
        self.assertIn("result_axes_v1", features.FEATURES)
        protocol = (Path(__file__).resolve().parents[1] / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("`result_axes_v1`", protocol)


if __name__ == "__main__":
    unittest.main()
