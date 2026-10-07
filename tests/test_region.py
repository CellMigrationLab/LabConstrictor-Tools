"""RegionOf: declaration rules, the schema flag, and the bbox helper (box, shape check, empty region)."""

import unittest
from typing import Annotated, Optional

import _paths  # noqa: F401  (must come first)
import numpy as np

from labconstrictor_tools import Image, Labels, RegionOf, Scalars, tool
from labconstrictor_tools.introspection import DeclarationError, describe_tool
from labconstrictor_tools.region import bbox
from labconstrictor_tools.types import ToolError


def schema(fn):
    return describe_tool(fn.__lc_tool__)["inputs"]


class Declaration(unittest.TestCase):
    def test_region_reaches_the_schema(self):
        @tool("R ok")
        def ok(image: Image, region: Annotated[Optional[Labels], RegionOf("image")] = None) -> Scalars:
            return {}

        inputs = {i["name"]: i for i in schema(ok)}
        self.assertEqual(inputs["region"]["region_of"], "image")
        self.assertTrue(inputs["region"]["nullable"])

    def test_refusals_are_readable(self):
        @tool("R required")
        def required(image: Image, region: Annotated[Labels, RegionOf("image")]) -> Scalars:
            return {}

        @tool("R not labels")
        def not_labels(image: Image, region: Annotated[Optional[Image], RegionOf("image")] = None) -> Scalars:
            return {}

        @tool("R unknown")
        def unknown(image: Image, region: Annotated[Optional[Labels], RegionOf("nothing")] = None) -> Scalars:
            return {}

        @tool("R not an image")
        def not_image(count: int, region: Annotated[Optional[Labels], RegionOf("count")] = None) -> Scalars:
            return {}

        for fn, word in ((required, "optional Labels"), (not_labels, "optional Labels"), (unknown, "Image parameter"), (not_image, "Image parameter")):
            with self.subTest(fn.__name__):
                with self.assertRaisesRegex(DeclarationError, word):
                    schema(fn)


class Box(unittest.TestCase):
    def test_box_encloses_every_selected_pixel(self):
        mask = np.zeros((20, 30), int)
        mask[3:6, 10:12] = 1
        mask[15, 25] = 2
        rows, columns = bbox(mask)
        self.assertEqual((rows, columns), (slice(3, 16), slice(10, 26)))
        self.assertEqual(np.zeros((20, 30))[rows, columns].shape, (13, 16))

    def test_the_image_size_is_checked(self):
        mask = np.ones((5, 5), int)
        self.assertEqual(bbox(mask, np.zeros((5, 5))), (slice(0, 5), slice(0, 5)))
        self.assertEqual(bbox(mask, np.zeros((3, 5, 5))), (slice(0, 5), slice(0, 5)))  # leading axes are ignored
        with self.assertRaisesRegex(ToolError, "size of the image"):
            bbox(mask, np.zeros((6, 5)))

    def test_an_empty_region_is_an_error_not_the_whole_image(self):
        with self.assertRaises(ToolError) as caught:
            bbox(np.zeros((4, 4), int))
        self.assertEqual(caught.exception.code, "empty_region")

    def test_wrong_dimensions_are_refused(self):
        with self.assertRaisesRegex(ToolError, "2D"):
            bbox(np.ones((2, 4, 4), int))


if __name__ == "__main__":
    unittest.main()
