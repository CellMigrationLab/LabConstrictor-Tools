"""Input/output conversion must never change a scientific value silently: dtype narrowing, defaults, booleans, choices, enums."""

import enum
import unittest
from typing import Annotated, Literal, Optional

import _paths  # noqa: F401  (must come first)
import numpy as np

from labconstrictor_tools import EnabledWhen, Image, Scalars, convert, tool
from labconstrictor_tools.introspection import DeclarationError, describe_tool
from labconstrictor_tools.types import ToolError


def schema_of(fn):
    return describe_tool(fn.__lc_tool__)


class Mode(enum.Enum):
    FAST = "fast"
    SAFE = "safe"


class PortableDtype(unittest.TestCase):
    def test_a_uint32_that_float32_cannot_hold_is_refused_not_rounded(self):
        with self.assertRaises(ToolError) as caught:
            convert.portable_dtype(np.array([16777217], dtype=np.uint32), "labels")
        self.assertEqual(caught.exception.code, "unsupported_dtype")
        self.assertIn("labels", caught.exception.message)

    def test_wide_integers_that_fit_16_bits_are_narrowed_without_changing_values(self):
        for dtype in (np.uint32, np.uint64, np.int32, np.int64):
            out = convert.portable_dtype(np.array([0, 7, 65535], dtype=dtype))
            self.assertEqual(out.dtype, np.uint16)
            self.assertEqual(out.tolist(), [0, 7, 65535])
        out = convert.portable_dtype(np.array([-5, 300], dtype=np.int64))
        self.assertEqual((out.dtype, out.tolist()), (np.int16, [-5, 300]))

    def test_large_integers_survive_when_float32_holds_them_exactly(self):
        out = convert.portable_dtype(np.array([0, 2**20, 70000 * 2], dtype=np.int64))
        self.assertEqual(out.dtype, np.float32)
        self.assertEqual(out.astype(np.int64).tolist(), [0, 2**20, 140000])

    def test_float64_beyond_float32_range_is_refused_but_inf_and_nan_pass(self):
        with self.assertRaises(ToolError):
            convert.portable_dtype(np.array([1e300]))
        out = convert.portable_dtype(np.array([np.nan, np.inf, 1.5]))
        self.assertEqual(out.dtype, np.float32)
        self.assertTrue(np.isnan(out[0]) and np.isinf(out[1]))

    def test_common_cases_are_unchanged(self):
        self.assertEqual(convert.portable_dtype(np.zeros(2, bool)).dtype, np.uint8)
        self.assertEqual(convert.portable_dtype(np.zeros(2, np.int8)).dtype, np.int16)
        self.assertEqual(convert.portable_dtype(np.zeros(2, np.uint16)).dtype, np.uint16)
        self.assertEqual(convert.portable_dtype(np.zeros(2, np.float64)).dtype, np.float32)


class Defaults(unittest.TestCase):
    def test_an_invalid_default_is_a_declaration_error(self):
        @tool("t")
        def bad_choice(mode: Literal["safe", "fast"] = "invalid") -> Scalars:
            return {}

        @tool("t2")
        def bad_int(x: int = "3") -> Scalars:  # type: ignore[assignment]
            return {}

        @tool("t3")
        def bad_bool(flag: bool = "yes") -> Scalars:  # type: ignore[assignment]
            return {}

        for fn in (bad_choice, bad_int, bad_bool):
            with self.assertRaises(DeclarationError, msg=fn.__name__):
                schema_of(fn)

    def test_optional_with_a_non_none_default_is_refused_explicitly(self):
        @tool("t")
        def odd(x: Optional[int] = 5) -> Scalars:
            return {}

        with self.assertRaises(DeclarationError) as caught:
            schema_of(odd)
        self.assertIn("Optional", str(caught.exception))

    def test_valid_defaults_and_unset_none_still_work(self):
        @tool("t")
        def fine(
            a: int = 3, b: float = 2, c: Optional[int] = None, d: Mode = Mode.SAFE, e: bool = False
        ) -> Scalars:
            return {}

        schema = schema_of(fine)
        by_name = {p["name"]: p for p in schema["inputs"]}
        self.assertEqual(
            (by_name["a"]["default"], by_name["d"]["default"], by_name["e"]["default"]), (3, "safe", False)
        )
        self.assertTrue(by_name["c"]["nullable"])


class StrictValues(unittest.TestCase):
    def param(self, kind, **extra):
        return {"name": "x", "label": "X", "type": kind, "required": True, **extra}

    def test_a_boolean_must_be_a_boolean(self):
        for bad in ("false", "true", 0, 1, "", None.__class__):
            with self.assertRaises(ToolError, msg=repr(bad)):
                convert._load_one(self.param("boolean"), bad)
        self.assertIs(convert._load_one(self.param("boolean"), False), False)

    def test_choices_compare_type_as_well_as_value(self):
        param = self.param("choice", choices=[1, 2])
        with self.assertRaises(ToolError):
            convert._load_one(param, True)  # True == 1 in Python
        self.assertEqual(convert._load_one(param, 2), 2)
        self.assertEqual(convert._load_one(self.param("choice", choices=["a"]), "a"), "a")

    def test_a_float_is_not_a_boolean(self):
        with self.assertRaises(ToolError):
            convert._load_one(self.param("float"), True)
        self.assertEqual(convert._load_one(self.param("float"), 2), 2.0)

    def test_an_empty_shared_memory_image_is_refused(self):
        from multiprocessing import shared_memory

        shm = shared_memory.SharedMemory(create=True, size=16)
        try:
            descriptor = {
                "appose_type": "ndarray",
                "shm": {"name": shm.name},
                "shape": [0, 512],
                "dtype": "uint8",
            }
            with self.assertRaises(ToolError) as caught:
                convert._load_one({"name": "i", "label": "I", "type": "image"}, descriptor)
            self.assertEqual(caught.exception.code, "empty_image")
        finally:
            shm.close()
            shm.unlink()


class Enums(unittest.TestCase):
    def test_an_enum_parameter_arrives_as_the_enum_member(self):
        seen = {}

        @tool("t")
        def pick(mode: Mode, other: Mode = Mode.SAFE, maybe: Optional[Mode] = None) -> Scalars:
            seen.update(mode=mode, other=other, maybe=maybe)
            return {}

        kwargs = convert.load_inputs(schema_of(pick), {"mode": "fast"}, pick)
        pick(**kwargs)
        self.assertIs(seen["mode"], Mode.FAST)
        self.assertIs(seen["other"], Mode.SAFE)  # the default is restored too
        self.assertIsNone(seen["maybe"])
        self.assertIs(
            convert.load_inputs(schema_of(pick), {"mode": "safe", "maybe": "fast"}, pick)["maybe"], Mode.FAST
        )


class EnabledWhenKeepsFalsyValues(unittest.TestCase):
    def test_equals_false_zero_and_empty_text_are_kept(self):
        @tool("t")
        def gated(
            normalize: bool = True,
            a: Annotated[float, EnabledWhen("normalize", False)] = 1.0,
            image: Optional[Image] = None,
        ) -> Scalars:
            return {}

        rule = {p["name"]: p for p in schema_of(gated)["inputs"]}["a"]["enabled_when"]
        self.assertEqual(rule, {"param": "normalize", "equals": [False]})


if __name__ == "__main__":
    unittest.main()
