"""#52: an output name is a file name in the result folder. Unsafe names are refused when the tool is declared, and every writer
(image, labels, table, points, shapes) keeps its file inside the job folder, so no file outside it is ever created or changed.
"""

import os
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

UNSAFE = [
    "../x", "../other_run/result", "/tmp/x", "x/y", "..\\x", "C:\\x", "C:x", "\\\\server\\share\\x", "x\\y", "..", ".",
    "", "   ", "a\x00b", "a\nb", "x.", "x ", " x", "CON", "nul", "COM1", "lpt9.txt", "a<b", "a|b", "a?b", "a*b", 'a"b',
]  # fmt: skip
SAFE = ["image", "results folder", "cell-area_2", "a.b", "Ünïcode", "x2", "COM10", "console"]

OUTPUT_ANNOTATIONS = {
    "image": T.ImageOut,
    "labels": T.LabelsOut,
    "table": T.TableOut,
    "points": T.PointsOut,
    "shapes": T.ShapesOut,
}
VALUES = {
    "image": np.zeros((4, 5), np.uint8),
    "labels": np.ones((4, 5), np.uint16),
    "table": {"a": [1, 2]},
    "points": {"y": [1.0], "x": [2.0]},
    "shapes": [[(0, 0), (0, 3), (3, 3)]],
}


def declare(kind, name):
    annotation = Annotated[OUTPUT_ANNOTATIONS[kind], T.Name(name)]

    def fn() -> annotation:  # type: ignore[valid-type]
        return VALUES[kind]

    return describe_tool(Tool(id="t", label="T", fn=fn))


class Declaration(unittest.TestCase):
    def test_unsafe_names_are_a_declaration_error_for_every_output_type(self):
        for kind in OUTPUT_ANNOTATIONS:
            for name in UNSAFE:
                with self.subTest(kind=kind, name=name):
                    with self.assertRaises(DeclarationError) as caught:
                        declare(kind, name)
                    self.assertIn("Name(", str(caught.exception))

    def test_safe_names_still_work(self):
        for name in SAFE:
            with self.subTest(name=name):
                self.assertEqual(declare("image", name)["outputs"][0]["name"], name)

    def test_unnamed_outputs_keep_their_automatic_names(self):
        def fn() -> tuple[T.ImageOut, T.ImageOut]:
            return VALUES["image"], VALUES["image"]

        schema = describe_tool(Tool(id="t", label="T", fn=fn))
        self.assertEqual([o["name"] for o in schema["outputs"]], ["image", "image2"])


class Writers(unittest.TestCase):
    """Defence in depth: a schema that did not come from `describe_tool` still cannot write outside the job folder."""

    def run_writer(self, kind, name):
        base = Path(tempfile.mkdtemp())
        job = base / "job"
        job.mkdir()
        (base / "outside.tif").write_bytes(b"keep")
        before = sorted(os.listdir(base))
        try:
            return (
                convert.build_results({"outputs": [{"name": name, "type": kind}]}, VALUES[kind], job),
                base,
                job,
                before,
            )
        except ToolError as error:
            return error, base, job, before

    def test_every_writer_refuses_a_name_that_leaves_the_job_folder(self):
        for kind in OUTPUT_ANNOTATIONS:
            for name in (
                "../outside",
                "../other_run/result",
                "sub/dir",
                str(Path(tempfile.gettempdir()) / "abs_output"),
            ):
                with self.subTest(kind=kind, name=name):
                    got, base, job, before = self.run_writer(kind, name)
                    self.assertIsInstance(got, ToolError)
                    self.assertEqual(got.code, "bad_return")
                    self.assertEqual(sorted(os.listdir(base)), before)
                    self.assertEqual(os.listdir(job), [])
                    self.assertEqual((base / "outside.tif").read_bytes(), b"keep")

    def test_every_writer_writes_a_safe_name_inside_the_job_folder(self):
        for kind in OUTPUT_ANNOTATIONS:
            with self.subTest(kind=kind):
                got, base, job, _ = self.run_writer(kind, "cell area")
                self.assertEqual(Path(got[0]["path"]).parent.resolve(), job.resolve())
                self.assertTrue(Path(got[0]["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
