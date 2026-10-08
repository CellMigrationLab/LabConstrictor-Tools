import enum
import json
import unittest
from typing import Annotated, Literal

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import (
    Affine,
    ApplyTo,
    Axes,
    ChoicesFrom,
    ClearAfterRun,
    Collapsed,
    Description,
    File,
    Group,
    Image,
    ImageOut,
    Label,
    Labels,
    Max,
    Min,
    Name,
    PickChannel,
    PixelSizeOf,
    Replace,
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


class InteractionHintTests(unittest.TestCase):
    def setUp(self):
        decorators.clear()

    def tearDown(self):
        decorators.clear()

    def _app(self):
        @tool
        def conditions(folder: str, user: str = "me") -> Scalars:
            return {"choices": ["a", "b"]}

        @tool
        def play(
            folder: str,
            user: str = "me",
            guess: Annotated[
                str, ChoicesFrom("conditions", depends=["folder", "user"]), ClearAfterRun()
            ] = "",
            extra: Annotated[int, Group("More"), Collapsed()] = 1,
        ) -> Annotated[ImageOut, Name("view"), Replace()]:
            return None

        return describe_tools()

    def test_schema_keys(self):
        play = {t["id"]: t for t in self._app()["tools"]}["play"]
        inputs = {i["name"]: i for i in play["inputs"]}
        self.assertEqual(
            inputs["guess"]["choices_from"],
            {"tool": "conditions", "depends": ["folder", "user"], "field": "choices"},
        )
        self.assertTrue(inputs["guess"]["clear_after_run"])
        self.assertTrue(inputs["extra"]["group_collapsed"])
        self.assertTrue(play["outputs"][0]["replace"])
        json.dumps(play)

    def test_plain_parameters_carry_no_hint_keys(self):
        play = {t["id"]: t for t in self._app()["tools"]}["play"]
        folder = {i["name"]: i for i in play["inputs"]}["folder"]
        for key in ("choices_from", "clear_after_run", "group_collapsed"):
            self.assertNotIn(key, folder)

    def test_unknown_source_tool_refused(self):
        @tool
        def play(g: Annotated[str, ChoicesFrom("nope")] = "") -> Scalars:
            return {}

        with self.assertRaisesRegex(DeclarationError, "names no tool"):
            describe_tools()

    def test_source_must_be_callable_from_depends(self):
        @tool
        def conditions(folder: str) -> Scalars:
            return {"choices": []}

        @tool
        def play(g: Annotated[str, ChoicesFrom("conditions")] = "") -> Scalars:
            return {}

        with self.assertRaisesRegex(DeclarationError, "required parameter 'folder'"):
            describe_tools()

    def test_depends_must_exist_in_both(self):
        @tool
        def conditions(folder: str) -> Scalars:
            return {"choices": []}

        @tool
        def play(
            folder: str, g: Annotated[str, ChoicesFrom("conditions", depends=["folder", "ghost"])] = ""
        ) -> Scalars:
            return {}

        with self.assertRaisesRegex(DeclarationError, "ghost"):
            describe_tools()

    def test_source_must_return_scalars(self):
        @tool
        def conditions() -> ImageOut:
            return None

        @tool
        def play(g: Annotated[str, ChoicesFrom("conditions")] = "") -> Scalars:
            return {}

        with self.assertRaisesRegex(DeclarationError, "must return Scalars"):
            describe_tools()

    def test_choices_only_for_strings_collapsed_needs_group_replace_only_for_data(self):
        @tool
        def a(n: Annotated[int, ChoicesFrom("a")] = 1) -> Scalars:
            return {}

        with self.assertRaisesRegex(DeclarationError, "only applies to a string"):
            describe_tools()
        decorators.clear()

        @tool
        def b(n: Annotated[int, Collapsed()] = 1) -> Scalars:
            return {}

        with self.assertRaisesRegex(DeclarationError, "needs a Group"):
            describe_tools()
        decorators.clear()

        @tool
        def c(n: int = 1) -> Annotated[Scalars, Replace()]:
            return {}

        with self.assertRaisesRegex(DeclarationError, "Replace applies"):
            describe_tools()

    def test_replace_applies_to_an_affine_output(self):
        import numpy as np

        @tool
        def align(image: Image) -> Annotated[Affine, ApplyTo("image"), Name("alignment"), Replace()]:
            return np.eye(3)

        out = describe_tools()["tools"][0]["outputs"][0]
        self.assertEqual((out["type"], out["replace"]), ("affine", True))


class PickChannelTests(unittest.TestCase):
    def setUp(self):
        decorators.clear()

    def tearDown(self):
        decorators.clear()

    def test_schema_key(self):
        @tool
        def one(image: Annotated[Image, Axes("YX"), PickChannel()]) -> Scalars:
            return {}

        param = describe_tools()["tools"][0]["inputs"][0]
        self.assertTrue(param["pick_channel"])
        self.assertEqual(param["axes"], "YX")

    def test_absent_without_the_marker(self):
        @tool
        def one(image: Image) -> Scalars:
            return {}

        self.assertNotIn("pick_channel", describe_tools()["tools"][0]["inputs"][0])

    def test_only_for_images(self):
        @tool
        def bad(n: Annotated[int, PickChannel()] = 1) -> Scalars:
            return {}

        with self.assertRaisesRegex(DeclarationError, "applies to an Image input"):
            describe_tools()

    def test_the_tool_must_want_a_2d_image(self):
        @tool
        def bad(image: Annotated[Image, Axes("ZYX"), PickChannel()]) -> Scalars:
            return {}

        with self.assertRaisesRegex(DeclarationError, "Axes must be YX"):
            describe_tools()


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ---- Widget hint (slider / radio)
def _desc(fn):
    from labconstrictor_tools.introspection import describe_tool

    return describe_tool(fn.__lc_tool__)["inputs"]


def test_widget_slider_and_radio_reach_the_schema():
    from typing import Annotated, Literal

    from labconstrictor_tools import Max, Min, Scalars, Widget, tool

    @tool("W")
    def w(
        x: Annotated[float, Min(0), Max(1), Widget("slider")] = 0.5,
        mode: Annotated[Literal["a", "b", "c"], Widget("radio")] = "a",
    ) -> Scalars:
        return {}

    ins = {i["name"]: i for i in _desc(w)}
    assert ins["x"]["widget"] == "slider" and ins["mode"]["widget"] == "radio"


def test_widget_declaration_errors_are_readable():
    from typing import Annotated, Literal

    import pytest

    from labconstrictor_tools import Scalars, Widget, tool
    from labconstrictor_tools.introspection import DeclarationError

    @tool("S1")
    def s1(x: Annotated[float, Widget("slider")] = 0.5) -> Scalars:  # no Min / Max
        return {}

    @tool("S2")
    def s2(x: Annotated[str, Widget("slider")] = "a") -> Scalars:  # not a number
        return {}

    @tool("R1")
    def r1(x: Annotated[Literal["a"], Widget("radio")] = "a") -> Scalars:  # one option
        return {}

    @tool("R2")
    def r2(
        x: Annotated[Literal["a", "b", "c", "d", "e", "f"], Widget("radio")] = "a",
    ) -> Scalars:  # six options
        return {}

    for fn, word in ((s1, "Min and Max"), (s2, "Min and Max"), (r1, "2 to 5"), (r2, "2 to 5")):
        with pytest.raises(DeclarationError, match=word):
            _desc(fn)
    with pytest.raises(ValueError, match="slider"):
        Widget("dial")
