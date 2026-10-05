import enum
import json
import unittest
from typing import Annotated, Literal

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import (
    Affine,
    ApplyTo,
    Axes,
    Description,
    File,
    Image,
    ImageOut,
    Label,
    Labels,
    Max,
    Min,
    Name,
    PixelSizeOf,
    Scalars,
    Table,
    TableOut,
    Unit,
    decorators,
    tool,
)
from labconstrictor_tools.introspection import DeclarationError, describe_tool, describe_tools


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class IntrospectionTests(unittest.TestCase):
    def setUp(self):
        decorators.clear()

    def test_scalar_types_defaults_required(self):
        @tool("T")
        def t(
            a: str,
            b: int = 3,
            c: float = 0.5,
            d: bool = True,
            e: str | None = None,
            f: "int | None" = None,
        ):
            "Doc."

        s = {i["name"]: i for i in describe_tool(t.__lc_tool__)["inputs"]}
        self.assertEqual((s["a"]["type"], s["a"]["required"]), ("string", True))
        self.assertEqual((s["b"]["type"], s["b"]["default"], s["b"]["required"]), ("integer", 3, False))
        self.assertEqual((s["c"]["type"], s["c"]["default"]), ("float", 0.5))
        self.assertEqual((s["d"]["type"], s["d"]["default"]), ("boolean", True))
        self.assertFalse(s["e"]["required"])
        self.assertNotIn("default", s["e"])

    def test_literal_enum_choices(self):
        @tool()
        def t(m: Literal["A", "B"] = "B", c: Color = Color.BLUE, req: Literal["x", "y"] = "x"):
            pass

        s = {i["name"]: i for i in describe_tool(t.__lc_tool__)["inputs"]}
        self.assertEqual(s["m"]["choices"], ["A", "B"])
        self.assertEqual(s["m"]["default"], "B")
        self.assertEqual(s["c"]["choices"], ["red", "blue"])
        self.assertEqual(s["c"]["default"], "blue")

    def test_annotated_metadata(self):
        @tool()
        def t(
            x: Annotated[float, Min(0), Max(1), Unit("um/px"), Description("thr"), Label("Threshold")] = 0.5,
            n: Annotated[int, Min(1)] = 2,
        ):
            pass

        s = {i["name"]: i for i in describe_tool(t.__lc_tool__)["inputs"]}
        self.assertEqual(
            (s["x"]["minimum"], s["x"]["maximum"], s["x"]["unit"], s["x"]["description"], s["x"]["label"]),
            (0, 1, "um/px", "thr", "Threshold"),
        )
        self.assertEqual(s["n"]["minimum"], 1)
        self.assertNotIn("maximum", s["n"])

    def test_docstring_args_become_descriptions(self):
        @tool()
        def t(a: int = 1, b: int = 2):
            """Summary line.

            Args:
                a: first one
                b (int): second
                    continues here
            """

        d = describe_tool(t.__lc_tool__)
        s = {i["name"]: i for i in d["inputs"]}
        self.assertEqual(d["description"], "Summary line.")
        self.assertEqual(s["a"]["description"], "first one")
        self.assertEqual(s["b"]["description"], "second continues here")

    def test_image_table_file_types(self):
        from pathlib import Path as P

        @tool()
        def t(
            img: Annotated[Image, Axes("YX")],
            opt: Image | None = None,
            tab: Table = None,
            f: File = None,
            p: P = None,
            lab: Labels = None,
        ):
            pass

        s = {i["name"]: i for i in describe_tool(t.__lc_tool__)["inputs"]}
        self.assertEqual((s["img"]["type"], s["img"]["axes"], s["img"]["required"]), ("image", "YX", True))
        self.assertEqual((s["opt"]["type"], s["opt"]["required"]), ("image", False))
        self.assertEqual(
            [s[k]["type"] for k in ("tab", "f", "p", "lab")], ["table", "file", "file", "labels"]
        )

    def test_outputs(self):
        @tool()
        def t(q: Image, r: Image) -> tuple[
            Annotated[Affine, ApplyTo("q", "r"), Name("alignment")],
            Annotated[ImageOut, Name("aligned"), Axes("YX")],
            TableOut,
            Scalars,
        ]:
            pass

        o = describe_tool(t.__lc_tool__)["outputs"]
        self.assertEqual([x["type"] for x in o], ["affine", "image", "table", "values"])
        self.assertEqual(o[0]["display"], {"apply_to": "q", "relative_to": "r"})
        self.assertEqual(o[1]["axes"], "YX")
        self.assertEqual([x["name"] for x in o], ["alignment", "aligned", "table", "values"])

    def test_single_and_no_output(self):
        @tool()
        def a() -> TableOut:
            pass

        @tool()
        def b():
            pass

        self.assertEqual(describe_tool(a.__lc_tool__)["outputs"][0]["name"], "table")
        self.assertEqual(describe_tool(b.__lc_tool__)["outputs"], [])

    def test_pixel_size_link(self):
        @tool()
        def t(img: Image, px: Annotated[float, PixelSizeOf("img")] = 1.0):
            pass

        self.assertEqual(describe_tool(t.__lc_tool__)["inputs"][1]["pixel_size_of"], "img")

    def test_invalid_declarations(self):
        @tool()
        def bad1(x):
            pass

        with self.assertRaisesRegex(DeclarationError, "no type annotation"):
            describe_tool(bad1.__lc_tool__)

        @tool()
        def bad2(x: list):
            pass

        with self.assertRaisesRegex(DeclarationError, "unsupported annotation"):
            describe_tool(bad2.__lc_tool__)

        @tool()
        def bad3(x: Annotated[int, Min(5)] = 1):
            pass

        with self.assertRaisesRegex(DeclarationError, "violates minimum"):
            describe_tool(bad3.__lc_tool__)

        @tool()
        def bad4(x: Annotated[float, PixelSizeOf("nope")] = 1.0):
            pass

        with self.assertRaisesRegex(DeclarationError, "names no parameter"):
            describe_tool(bad4.__lc_tool__)

        @tool()
        def bad5(a: Image) -> Annotated[Affine, ApplyTo("zzz")]:
            pass

        with self.assertRaisesRegex(DeclarationError, "unknown parameter"):
            describe_tool(bad5.__lc_tool__)

        @tool()
        def bad6() -> int:
            pass

        with self.assertRaisesRegex(DeclarationError, "unsupported return"):
            describe_tool(bad6.__lc_tool__)

    def test_duplicate_ids(self):
        @tool(id="same")
        def a():
            pass

        with self.assertRaisesRegex(ValueError, "duplicate tool id"):

            @tool(id="same")
            def b():
                pass

    def test_deterministic_and_json(self):
        @tool("Z")
        def zz(a: int = 1):
            pass

        @tool("A")
        def aa(b: Literal["u"] = "u"):
            pass

        s1, s2 = describe_tools(), describe_tools()
        self.assertEqual(json.dumps(s1), json.dumps(s2))
        self.assertEqual([t["id"] for t in s1["tools"]], ["aa", "zz"])
        self.assertEqual(s1["protocol"], 1)

    def test_describe_does_not_call_tool(self):
        called = []

        @tool()
        def t(a: int = 1):
            called.append(1)

        describe_tools()
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
