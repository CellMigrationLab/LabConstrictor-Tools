"""Error codes and wording of the value rules, as docs/PROTOCOL.md promises them: a wrong value, a wrong return, a stale
shared-memory block, an image no host can open and a misused hint are each a ToolError (or DeclarationError) with a readable
message, never a raw Python exception. The exact texts are the contract the Groovy hosts and the Napari plugin mirror.
"""

import unittest
import warnings
from multiprocessing import shared_memory
from typing import Annotated

import _paths  # noqa: F401  (must come first)
import numpy as np

from labconstrictor_tools import convert, tool
from labconstrictor_tools import types as T
from labconstrictor_tools.introspection import DeclarationError, describe_tool
from labconstrictor_tools.types import ToolError


def param(kind, **extra):
    return {"name": "n", "label": "N", "type": kind, "required": True, **extra}


def load(kind, value, **extra):
    return convert._load_one(param(kind, **extra), value)


def refused(call, *args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # an out-of-range cast would warn on x86 and be silent on ARM
        try:
            call(*args, **kwargs)
        except ToolError as error:
            return error
    raise AssertionError("accepted")


def result(kind, value, **extra):
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        return convert.build_results({"outputs": [{"name": "o", "type": kind, **extra}]}, value, folder)


class NumbersMustBeNumbers(unittest.TestCase):
    def test_integer_given_something_else_is_invalid_parameter_naming_what_arrived(self):
        for value, arrived in (("abc", "text"), ([1], "a list"), ({}, "an object"), (None, "nothing (None)")):
            with self.subTest(value=value):
                error = refused(load, "integer", value)
                self.assertEqual(error.code, "invalid_parameter")
                self.assertEqual(error.message, "'N' must be an integer, got %s" % arrived)

    def test_integer_that_is_not_whole_or_not_finite(self):
        for value in (1.5, float("inf"), float("nan"), True):
            with self.subTest(value=value):
                self.assertEqual(refused(load, "integer", value).code, "invalid_parameter")
        self.assertEqual(load("integer", 3.0), 3)

    def test_float_given_something_else_or_beyond_the_float_range(self):
        self.assertEqual(refused(load, "float", "1.5").message, "'N' must be a number, got text")
        self.assertEqual(refused(load, "float", 10**400).message, "'N' must be a finite number")
        self.assertEqual(load("float", 2), 2.0)


class PathsMustBeText(unittest.TestCase):
    def test_file_folder_and_image_given_a_non_text_value(self):
        for kind in ("file", "folder", "image"):
            for value, arrived in (([1], "a list"), (5, "an integer"), ({}, "an object")):
                with self.subTest(kind=kind, value=value):
                    error = refused(load, kind, value)
                    self.assertEqual(error.code, "invalid_parameter")
                    self.assertEqual(
                        error.message,
                        "'N' must be a path (text), got %s: the host must send the file or folder path as text"
                        % arrived,
                    )


class SharedMemoryDescriptors(unittest.TestCase):
    def descriptor(self, **changes):
        base = {
            "appose_type": "ndarray",
            "shm": {"name": "lc_no_such_block"},
            "shape": [2, 2],
            "dtype": "uint8",
        }
        return {**base, **changes}

    def test_a_block_that_is_gone_or_a_descriptor_with_missing_or_wrong_fields(self):
        cases = {
            "gone": self.descriptor(),
            "no-shm": {"appose_type": "ndarray", "shape": [1], "dtype": "uint8"},
            "shm-not-an-object": self.descriptor(shm=5),
            "name-not-text": self.descriptor(shm={"name": 5}),
            "no-dtype": {k: v for k, v in self.descriptor().items() if k != "dtype"},
            "no-shape": {k: v for k, v in self.descriptor().items() if k != "shape"},
            "bad-dtype": self.descriptor(dtype="nonsense"),
            "object-dtype": self.descriptor(dtype="object"),
            "shape-not-a-list": self.descriptor(shape=5),
        }
        for label, descriptor in cases.items():
            with self.subTest(label):
                error = refused(load, "image", descriptor)
                self.assertEqual(error.code, "unreadable_image")
                self.assertIn("the shared-memory image for 'N' is gone or malformed", error.message)
                self.assertIn("the host must keep the block alive until the task ends", error.message)

    def test_a_shape_larger_than_the_block_or_negative(self):
        block = shared_memory.SharedMemory(create=True, size=16)
        try:
            too_big = block.size + (
                1 << 16
            )  # beyond the real block even where blocks are rounded up to whole pages
            for shape in ([too_big, 1], [-1, 4]):
                with self.subTest(shape=shape):
                    descriptor = self.descriptor(shm={"name": block.name}, shape=shape)
                    self.assertEqual(refused(load, "image", descriptor).code, "unreadable_image")
            good = load("image", self.descriptor(shm={"name": block.name}, shape=[4, 4]))
            self.assertEqual(good.shape, (4, 4))
        finally:
            block.close()
            block.unlink()


class WrongReturns(unittest.TestCase):
    def test_each_kind_of_wrong_value_names_the_output_and_what_was_expected(self):
        cases = [
            ("image", None, "the image output 'o' must be an array of numbers, got nothing (None)"),
            ("image", "text", "the image output 'o' must be an array of numbers, got text"),
            ("labels", {}, "the labels output 'o' must be an array of numbers, got an object"),
            (
                "table",
                5,
                "the table output 'o' must be a DataFrame, a dict of lists or a list of dicts, got an integer",
            ),
            ("values", [1, 2], "the values output 'o' must be a dict of JSON-able values, got a list"),
            ("file", 5, "the file output 'o' must be a path (pathlib.Path or text), got an integer"),
            ("message", 5, "the message output 'o' must be text, got an integer"),
            (
                "points",
                False,
                "the points output 'o' must be a DataFrame, a dict of lists or a list of dicts, got true/false",
            ),
        ]
        for kind, value, message in cases:
            with self.subTest(kind=kind, value=value):
                error = refused(result, kind, value)
                self.assertEqual((error.code, error.message), ("bad_return", message))

    def test_table_like_mistakes_are_bad_return_whatever_the_pandas_version(self):
        mistakes = [
            [{}, None],
            [1, 2],
            [{"a": 1}, [1]],
            ["a", {}],
            {"a": {"b": 1}},
            {"a": [1, 2], "b": [1]},
            {"a": 1},
            [[1, 2], [3]],
            [None],
            "abc",
            {1, 2},
            np.array(5),
            np.zeros((2, 2)),
            iter([1]),
            {"a": np.zeros((2, 2))},
        ]
        for kind in ("table", "points"):
            for value in mistakes:
                with self.subTest(kind=kind, value=repr(value)[:30]):
                    self.assertEqual(refused(result, kind, value).code, "bad_return")
        self.assertIn("different lengths", refused(result, "table", {"a": [1, 2], "b": [1]}).message)

    def test_affine_that_is_ragged_text_or_not_a_matrix(self):
        for value in ([[1, 0, 0], [0, 1], [0, 0, 1]], [["a", 0, 0], [0, 1, 0], [0, 0, 1]], {}):
            with self.subTest(value=value):
                error = refused(result, "affine", value)
                self.assertEqual(error.code, "bad_return")
                self.assertIn("the affine output 'o' must be a 3x3 matrix of numbers", error.message)

    def test_affine_with_nan_or_infinity_is_refused(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(bad=bad):
                error = refused(result, "affine", [[1, 0, bad], [0, 1, 0], [0, 0, 1]])
                self.assertEqual(error.code, "bad_return")
                self.assertIn("the affine output 'o' has a value that is not a finite number", error.message)

    def test_two_outputs_given_one_array_or_a_scalar_is_bad_return_not_a_crash(self):
        schema = {"outputs": [{"name": "a", "type": "image"}, {"name": "b", "type": "table"}]}
        for returned in (np.zeros((2, 2), np.uint8), 5, "ab"):
            with self.subTest(returned=type(returned).__name__):
                error = refused(convert.build_results, schema, returned, ".")
                self.assertEqual(error.code, "bad_return")
                self.assertIn("declared 2 outputs: return a tuple with one value per output", error.message)


class ImagesNoHostCanOpen(unittest.TestCase):
    def test_empty_arrays_are_bad_return(self):
        for shape in ((0, 3), (0,), (2, 0, 2)):
            with self.subTest(shape=shape):
                error = refused(convert.portable_dtype, np.zeros(shape, np.uint8), "image")
                self.assertEqual(error.code, "bad_return")
                self.assertIn("image is empty (shape %s)" % (shape,), error.message)

    def test_complex_object_and_text_arrays_are_unsupported_dtype(self):
        arrays = {
            "complex": np.zeros((2, 2), np.complex64),
            "object": np.array([[None, 1]], dtype=object),
            "text": np.array([["a", "b"]]),
            "bytes": np.array([[b"a"]]),
        }
        for label, array in arrays.items():
            with self.subTest(label):
                error = refused(convert.portable_dtype, array, "image")
                self.assertEqual(error.code, "unsupported_dtype")
                self.assertIn("hosts can only open numbers; return a numeric array", error.message)


class Float32Exactness(unittest.TestCase):
    """Never cast a float back to an integer type outside its range: x86 gives 0 and ARM saturates, so only a comparison that
    stays inside the range is exact on every CPU. numpy warns about the bad cast on x86, which these tests turn into failures.
    """

    def test_uint64_beyond_float32_is_refused_with_unsupported_dtype_on_every_cpu(self):
        for value in (2**64 - 1, 2**64 - 2**39, 2**63 + 1):
            with self.subTest(value=value):
                error = refused(convert.portable_dtype, np.array([[value, 1]], np.uint64))
                self.assertEqual(error.code, "unsupported_dtype")

    def test_int64_extremes_are_refused_or_exact_without_a_bad_cast(self):
        info = np.iinfo(np.int64)
        self.assertEqual(
            refused(convert.portable_dtype, np.array([info.max], np.int64)).code, "unsupported_dtype"
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            out = convert.portable_dtype(np.array([info.min, 2**40], np.int64))  # powers of two are exact
        self.assertEqual((out.dtype, out.tolist()), (np.float32, [float(info.min), float(2**40)]))

    def test_uint64_that_float32_holds_exactly_is_kept(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            out = convert.portable_dtype(np.array([2**63, 2**40 * 3], np.uint64))
        self.assertEqual((out.dtype, out.tolist()), (np.float32, [float(2**63), float(2**40 * 3)]))


def describe(fn):
    """The real @tool decorator, then the real describe_tool: the DeclarationError an author sees at registration."""
    return describe_tool(tool("t")(fn).__lc_tool__)


def declaration_error(fn):
    try:
        describe(fn)
    except DeclarationError as error:
        return str(error)
    raise AssertionError("accepted")


class HintMisuse(unittest.TestCase):
    """The wording of each refusal: it names the parameter (or tool), the hint and the fix."""

    def test_bounds_on_text_and_an_empty_range(self):
        def min_on_text(p: Annotated[str, T.Min(0)]) -> T.Scalars: ...

        def min_above_max(p: Annotated[int, T.Min(5), T.Max(1)]) -> T.Scalars: ...

        def bound_not_a_number(p: Annotated[int, T.Min("a")]) -> T.Scalars: ...

        self.assertEqual(
            declaration_error(min_on_text),
            "parameter 'p': Min applies to an int or float parameter; this one is of type string: remove it",
        )
        self.assertEqual(
            declaration_error(min_above_max),
            "parameter 'p': Min(5) is above Max(1), so no value is allowed: swap them or widen the range",
        )
        self.assertEqual(
            declaration_error(bound_not_a_number), "parameter 'p': Min('a') must be a finite number"
        )

    def test_axes_and_pixel_size_on_the_wrong_type(self):
        def axes_on_text(p: Annotated[str, T.Axes("YX")]) -> T.Scalars: ...

        def axes_on_table(p: Annotated[T.Table, T.Axes("YX")]) -> T.Scalars: ...

        def pixel_size_on_int(image: T.Image, p: Annotated[int, T.PixelSizeOf("image")]) -> T.Scalars: ...

        def axes_on_a_table_output(image: T.Image) -> Annotated[T.TableOut, T.Axes("YX")]: ...

        self.assertEqual(
            declaration_error(axes_on_text),
            "parameter 'p': Axes describes the dimensions of an Image or Labels input and this parameter is not one: remove it",
        )
        self.assertEqual(
            declaration_error(axes_on_table),
            "parameter 'p': Axes describes the dimensions of an Image or Labels input and this parameter is not one: remove it",
        )
        self.assertEqual(
            declaration_error(pixel_size_on_int),
            "parameter 'p': PixelSizeOf applies to a float parameter (the calibration in um/px); this one is of type integer: remove it",
        )
        self.assertEqual(
            declaration_error(axes_on_a_table_output),
            "tool 'axes_on_a_table_output' output 0: Axes describes an image or labels output; this one is of type table: remove it",
        )

    def test_output_markers_on_an_input(self):
        def name_on_input(p: Annotated[str, T.Name("x")]) -> T.Scalars: ...

        def replace_on_input(p: Annotated[T.Image, T.Replace()]) -> T.Scalars: ...

        def apply_to_on_input(p: Annotated[str, T.ApplyTo("p")]) -> T.Scalars: ...

        for fn, marker in (
            (name_on_input, "Name"),
            (replace_on_input, "Replace"),
            (apply_to_on_input, "ApplyTo"),
        ):
            with self.subTest(marker):
                self.assertEqual(
                    declaration_error(fn),
                    "parameter 'p': %s describes a result, not an input: put it on the return annotation or remove it"
                    % marker,
                )

    def test_duplicate_output_names(self):
        def same(
            image: T.Image,
        ) -> tuple[Annotated[T.ImageOut, T.Name("same")], Annotated[T.TableOut, T.Name("same")]]: ...

        def collides(
            image: T.Image,
        ) -> tuple[T.ImageOut, T.ImageOut, Annotated[T.TableOut, T.Name("image2")]]: ...

        self.assertEqual(
            declaration_error(same),
            "tool 'same': two outputs are named 'same': give each output its own Name(...)",
        )
        self.assertIn("duplicate output names", declaration_error(collides))

    def test_unnamed_outputs_of_one_type_still_get_a_numeric_suffix(self):
        def two(image: T.Image) -> tuple[T.ImageOut, T.ImageOut]: ...

        self.assertEqual([o["name"] for o in describe(two)["outputs"]], ["image", "image2"])


if __name__ == "__main__":
    unittest.main()
