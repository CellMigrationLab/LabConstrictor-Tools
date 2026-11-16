"""How the worker stores result images: one grey page per plane, except an 8-bit Y X 3/4 colour image.

Left to itself, tifffile stored a (3, Y, X) or (4, Y, X) result (three channels, three timepoints) as one page of colour
samples, which Fiji cannot open unless it is 8-bit: Fast4DRegPy's "Align channels" on a 3-channel image showed nothing in Fiji.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import tifffile

from labconstrictor_tools import convert


def write(array: np.ndarray) -> tifffile.TiffFile:
    out = convert._write_one({"type": "image", "name": "result"}, array, Path(tempfile.mkdtemp()))
    return tifffile.TiffFile(out["path"])


class ResultTiffLayoutTests(unittest.TestCase):
    def test_three_or_four_planes_are_grey_pages(self) -> None:
        for shape in ((3, 8, 10), (4, 8, 10)):
            for dtype in (np.float32, np.uint16, np.uint8):
                array = np.arange(np.prod(shape), dtype=dtype).reshape(shape)
                with self.subTest(shape=shape, dtype=dtype), write(array) as tif:
                    self.assertEqual(len(tif.pages), shape[0])
                    self.assertEqual(tif.pages[0].shape, shape[1:])
                    self.assertEqual(tif.pages[0].photometric, tifffile.PHOTOMETRIC.MINISBLACK)
                    np.testing.assert_array_equal(tif.asarray(), array)

    def test_an_8bit_colour_image_stays_rgb(self) -> None:
        for samples in (3, 4):
            array = np.arange(8 * 10 * samples, dtype=np.uint8).reshape(8, 10, samples)
            with self.subTest(samples=samples), write(array) as tif:
                self.assertEqual(len(tif.pages), 1)
                self.assertEqual(tif.pages[0].photometric, tifffile.PHOTOMETRIC.RGB)
                np.testing.assert_array_equal(tif.asarray(), array)

    def test_other_shapes_keep_their_values_and_shape(self) -> None:
        for shape in ((8, 10), (5, 8, 10), (2, 3, 8, 10), (8, 10, 3)):
            array = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
            with self.subTest(shape=shape), write(array) as tif:
                self.assertEqual(tif.pages[0].photometric, tifffile.PHOTOMETRIC.MINISBLACK)
                np.testing.assert_array_equal(tif.asarray(), array)


if __name__ == "__main__":
    unittest.main()
