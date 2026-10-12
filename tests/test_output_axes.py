"""#53: a declared `Axes(...)` on an image or labels output is a promise about the written array. A result with another number of
dimensions is `bad_return` before any file is written, and the `axes` a host reads always match the file."""

import tempfile
import unittest
from pathlib import Path
from typing import Annotated

import _paths  # noqa: F401  (must come first)
import numpy as np

from labconstrictor_tools import convert
from labconstrictor_tools import types as T
from labconstrictor_tools.decorators import Tool
from labconstrictor_tools.introspection import DeclarationError, describe_tool
from labconstrictor_tools.types import ToolError

KINDS = {"image": T.ImageOut, "labels": T.LabelsOut}


def build(kind, array, axes=None):
    marker = [T.Axes(axes)] if axes is not None else []
    annotation = Annotated[(KINDS[kind], T.Name("out"), *marker)]

    def fn() -> annotation:  # type: ignore[valid-type]
        return array

    schema = describe_tool(Tool(id="t", label="T", fn=fn))
    folder = Path(tempfile.mkdtemp())
    try:
        return convert.build_results(schema, array, folder), folder
    except ToolError as error:
        return error, folder


class DeclaredAxes(unittest.TestCase):
    def test_a_matching_array_succeeds_and_the_manifest_agrees_with_the_file(self):
        import tifffile

        for kind in KINDS:
            for axes, shape in (
                ("YX", (4, 5)),
                ("ZYX", (3, 4, 5)),
                ("CZYX", (2, 3, 4, 5)),
                ("YXS", (4, 5, 3)),
            ):
                with self.subTest(kind=kind, axes=axes):
                    got, folder = build(kind, np.ones(shape, np.uint8), axes)
                    self.assertEqual(got[0]["axes"], axes)
                    self.assertEqual(tifffile.imread(got[0]["path"]).ndim, len(got[0]["axes"]))

    def test_a_3d_array_declared_yx_is_bad_return_and_nothing_is_written(self):
        for kind in KINDS:
            for axes, shape in (("YX", (10, 8, 8)), ("ZYX", (8, 8)), ("YX", (8,)), ("ZYX", (2, 3, 4, 5))):
                with self.subTest(kind=kind, axes=axes, shape=shape):
                    got, folder = build(kind, np.ones(shape, np.uint8), axes)
                    self.assertIsInstance(got, ToolError)
                    self.assertEqual(got.code, "bad_return")
                    for needle in ("%s output 'out'" % kind, axes, str(shape)):
                        self.assertIn(needle, str(got))
                    self.assertEqual(list(folder.iterdir()), [], "no misleading file")

    def test_without_axes_the_default_follows_the_array_and_never_claims_more(self):
        for kind in KINDS:
            for shape, expected in (
                ((4, 5), "YX"),
                ((3, 4, 5), "ZYX"),
                ((2, 3, 4, 5), "CZYX"),
                ((5,), ""),
                ((1, 2, 3, 4, 5), ""),
            ):
                with self.subTest(kind=kind, shape=shape):
                    got, _ = build(kind, np.ones(shape, np.uint8))
                    self.assertEqual(got[0]["axes"], expected)
                    self.assertIn(len(got[0]["axes"]), (0, len(shape)))


class AxisLabels(unittest.TestCase):
    def test_labels_outside_the_protocol_are_a_declaration_error(self):
        for axes in ("", "Q", "yx", "YY", "Y X", "YX1"):
            with self.subTest(axes=axes, where="output"):
                with self.assertRaises(DeclarationError) as caught:
                    build("image", np.ones((2, 2), np.uint8), axes)
                self.assertIn("Axes(", str(caught.exception))

            with self.subTest(axes=axes, where="input"):

                def fn(image: Annotated[T.Image, T.Axes(axes)]) -> T.Scalars:  # type: ignore[valid-type]
                    return {}

                with self.assertRaises(DeclarationError):
                    describe_tool(Tool(id="t", label="T", fn=fn))

    def test_every_permitted_label_is_accepted(self):
        for axes in ("YX", "ZYX", "TYX", "CYX", "TCZYX", "YXS"):
            with self.subTest(axes=axes):
                got, _ = build("image", np.ones((1,) * (len(axes) - 2) + (2, 2), np.uint8), axes)
                self.assertEqual(got[0]["axes"], axes)


if __name__ == "__main__":
    unittest.main()
