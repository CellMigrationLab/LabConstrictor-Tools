"""Property and fuzz tests (hypothesis) of the production converters and text helpers, run in this process.

Profiles: `ci` (default) derandomized, 200 examples per property; `nightly` (LC_HYPOTHESIS_PROFILE=nightly) random seeds, thousands
of examples. Every property compares with an oracle written in this file or in roundtrip_cases.py (plain Python and numpy),
never with the converter under test. A property that currently finds a real defect is listed in roundtrip_known_failures.py
(key `property:<name>`): it is skipped here and re-run by test_roundtrip_known_failures.py, which fails when it starts to pass.
"""

import ast
import csv
import json
import math
import os
import shlex
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
import numpy as np
import pandas as pd
import roundtrip_app
import roundtrip_cases as rc
import roundtrip_harness as harness
import roundtrip_profiles  # noqa: F401  (registers and loads the hypothesis profile)
import tifffile
from hypothesis import example, given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp
from roundtrip_known_failures import KNOWN, is_known

from labconstrictor_tools import cli, command, convert, protocol, testing
from labconstrictor_tools.types import ToolError

_DECLARED = roundtrip_app.declared(rc.APP_MODULE)
TOOLS = {tool_id: schema for tool_id, (schema, _) in _DECLARED.items()}
FUNCTIONS = {tool_id: function for tool_id, (_, function) in _DECLARED.items()}
same = harness.same

# ------------------------------------------------------------------------------------------------ strategies
JSON_LEAVES = st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=12)
JSON_VALUES = st.recursive(
    JSON_LEAVES,
    lambda inner: st.lists(inner, max_size=3) | st.dictionaries(st.text(max_size=4), inner, max_size=3),
    max_leaves=5,
)
FINITE = st.floats(allow_nan=False, allow_infinity=False)
TEXTS = st.text(max_size=60)  # any unicode except lone surrogates (they cannot be in a UTF-8 stream)
DTYPES = st.sampled_from([np.dtype(name) for name in rc.DTYPES])
IMAGES = DTYPES.flatmap(
    lambda dtype: hnp.arrays(dtype, hnp.array_shapes(min_dims=2, max_dims=3, min_side=1, max_side=5))
)


def call_loader(tool_id, name, value):
    """The production entry the worker uses for inputs: convert.load_inputs with the tool's own schema."""
    return convert.load_inputs(TOOLS[tool_id], {name: value}, FUNCTIONS[tool_id])


def tool_error_or_value(tool_id, name, value):
    try:
        return call_loader(tool_id, name, value)
    except ToolError as error:
        return error


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def arrays_equal(got, want):
    if got.dtype != want.dtype or got.shape != want.shape:
        return False
    if want.dtype.kind == "f":
        return bool(
            np.array_equal(got, want, equal_nan=True) and np.array_equal(np.signbit(got), np.signbit(want))
        )
    return bool(np.array_equal(got, want))


# ------------------------------------------------------------------------------ converters only raise ToolError
@given(JSON_VALUES)
def only_toolerror_integer(value):
    tool_error_or_value("echo_int", "value", value)


@given(JSON_VALUES)
def only_toolerror_float(value):
    tool_error_or_value("echo_float", "value", value)


@given(JSON_VALUES)
def only_toolerror_boolean(value):
    tool_error_or_value("echo_bool", "value", value)


@given(JSON_VALUES)
def only_toolerror_choice(value):
    tool_error_or_value("echo_choice", "value", value)


@given(JSON_VALUES)
def only_toolerror_enum(value):
    tool_error_or_value("echo_enum", "value", value)


@given(JSON_VALUES)
def only_toolerror_bounded(value):
    tool_error_or_value("echo_bounded_int", "value", value)
    tool_error_or_value("echo_bounded_float", "value", value)


@given(JSON_VALUES)
def only_toolerror_string(value):
    tool_error_or_value("echo_string", "value", value)


@given(TEXTS)
def only_toolerror_paths_given_as_text(text):
    for tool_id, name in (
        ("echo_image", "image"),
        ("echo_labels", "labels"),
        ("echo_folder", "folder"),
        ("echo_file", "file"),
    ):
        tool_error_or_value(tool_id, name, text)


@given(JSON_VALUES)
def only_toolerror_file_value(value):
    tool_error_or_value("echo_file", "file", value)


@given(JSON_VALUES)
def only_toolerror_folder_value(value):
    tool_error_or_value("echo_folder", "folder", value)


SHARED_MEMORY_DESCRIPTORS = st.fixed_dictionaries(
    {"appose_type": st.just("ndarray")},
    optional={"shm": JSON_VALUES, "shape": JSON_VALUES, "dtype": JSON_VALUES},
)


@given(SHARED_MEMORY_DESCRIPTORS)
def only_toolerror_image_shared_memory(descriptor):
    tool_error_or_value("echo_image", "image", descriptor)


@given(st.binary(max_size=200))
def only_toolerror_table_file(content):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "t.csv"
        path.write_bytes(content)
        tool_error_or_value("echo_table", "table", str(path))


# ----------------------------------------------- results: whatever a tool returns, a ToolError or a result, never a crash
def only_toolerror_results(kind, value):
    schema = {"outputs": [{"name": kind, "type": kind}]}
    with tempfile.TemporaryDirectory() as folder:
        try:
            convert.build_results(schema, value, folder)
        except ToolError:
            pass


@given(JSON_VALUES)
def only_toolerror_result_affine(value):
    only_toolerror_results("affine", value)


# shapes that crashed some pandas versions (found by hypothesis on Python 3.10): pinned so every Python and every run sees them
TABLE_LIKE_MISTAKES = (
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
    {"": [None, []]},
    {"a": np.zeros((2, 2))},
)


def with_table_examples(test):
    for mistake in TABLE_LIKE_MISTAKES:
        test = example(mistake)(test)
    return test


@with_table_examples
@given(JSON_VALUES)
def only_toolerror_result_points(value):
    only_toolerror_results("points", value)


@given(JSON_VALUES)
def only_toolerror_result_shapes(value):
    only_toolerror_results("shapes", value)


@with_table_examples
@given(JSON_VALUES)
def only_toolerror_result_table(value):
    only_toolerror_results("table", value)


@given(JSON_VALUES)
def only_toolerror_result_image(value):
    only_toolerror_results("image", value)


@given(JSON_VALUES)
def only_toolerror_result_values(value):
    only_toolerror_results("values", value)


@given(JSON_VALUES)
def only_toolerror_result_message(value):
    only_toolerror_results("message", value)


# ---------------------------------------------------------------------------------- scalars: identity and rules
@given(st.integers())
def identity_integer(value):
    out = call_loader("echo_int", "value", json.loads(json.dumps(value)))
    assert same(out["value"], value), (out, value)


@given(FINITE)
def identity_float(value):
    out = call_loader("echo_float", "value", json.loads(json.dumps(value)))
    assert same(out["value"], value), (out, value)


@given(st.integers(min_value=-(10**300), max_value=10**300))
def identity_float_from_integer(value):
    out = call_loader("echo_float", "value", value)
    assert same(out["value"], float(value)), (out, value)


@given(st.booleans())
def identity_boolean(value):
    assert same(call_loader("echo_bool", "value", value)["value"], value)


@given(TEXTS)
def identity_string(value):
    out = call_loader("echo_string", "value", json.loads(json.dumps(value)))
    assert same(out["value"], value), (out, value)


@given(st.sampled_from(["alpha", "beta", "gamma", "with space", "ünï", ""]))
def identity_choice(value):
    assert same(call_loader("echo_choice", "value", value)["value"], value)


@given(
    st.one_of(st.integers(-10, 10), st.floats(allow_nan=False, allow_infinity=False), st.booleans(), TEXTS)
)
def choice_accepts_exactly_the_declared_values(value):
    got = tool_error_or_value("echo_choice", "value", value)
    declared = ["alpha", "beta", "gamma", "with space", "ünï", ""]
    allowed = any(type(value) is type(c) and value == c for c in declared)
    assert isinstance(got, dict) == allowed, (value, got)
    if not allowed:
        assert got.code == "invalid_parameter"


@given(st.integers(min_value=-(10**30), max_value=10**30))
def integer_bounds_are_inclusive(value):
    got = tool_error_or_value("echo_bounded_int", "value", value)
    inside = -5 <= value <= 10
    assert isinstance(got, dict) == inside, (value, got)
    if inside:
        assert same(got["value"], value)
    else:
        assert got.code == "invalid_parameter"


@given(
    st.one_of(
        FINITE, st.sampled_from([-0.5, 1.5, math.nextafter(-0.5, -1), math.nextafter(1.5, 2), -0.0, 0.0])
    )
)
def float_bounds_are_inclusive(value):
    got = tool_error_or_value("echo_bounded_float", "value", value)
    inside = -0.5 <= value <= 1.5
    assert isinstance(got, dict) == inside, (value, got)
    if inside:
        assert same(got["value"], value)


@given(st.one_of(st.none(), st.integers(-(10**20), 10**20)))
def unset_never_becomes_zero_integer(value):
    got = call_loader("echo_optional_int", "value", value)
    assert same(got["value"], value), (value, got)


@given(st.one_of(st.none(), TEXTS))
def unset_never_becomes_empty_text(value):
    got = call_loader("echo_optional_string", "value", value)
    assert same(got["value"], value), (value, got)


@given(st.one_of(st.none(), st.booleans()))
def unset_never_becomes_false(value):
    got = call_loader("echo_optional_bool", "value", value)
    assert same(got["value"], value), (value, got)


@given(st.one_of(st.none(), FINITE))
def unset_never_becomes_zero_float(value):
    got = call_loader("echo_optional_float", "value", value)
    assert same(got["value"], value), (value, got)


# ------------------------------------------------------------------------------ files, images, tables, results
@given(IMAGES)
def image_input_and_output_round_trip(array):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "i.tif"
        tifffile.imwrite(path, array)
        got = call_loader("echo_image", "image", str(path))["image"]
        assert arrays_equal(got, array), (got.dtype, array.dtype)
        expected = rc.expected_image_out(array)
        try:
            results = convert.build_results(TOOLS["echo_image"], (array, {}), folder)
        except ToolError as error:
            assert expected is None and error.code == "unsupported_dtype", (error.code, array.dtype)
            return
        assert expected is not None, "a result that the oracle says cannot be stored was written"
        read = tifffile.imread(results[0]["path"])
        assert str(read.dtype) in expected.dtypes and read.shape == array.shape, (read.dtype, expected.dtypes)
        assert np.array_equal(read.astype(np.float64), expected.values.astype(np.float64), equal_nan=True)


@given(IMAGES)
def image_shared_memory_round_trip(array):
    session = harness.Session()
    try:
        descriptor = session._share(array)
        got = call_loader("echo_image", "image", descriptor)["image"]
        assert arrays_equal(got, array)
    finally:
        session.close()


def table_text():
    # CSV cannot tell "007" from 7, nor "NA" from a missing cell: texts that are unambiguous in CSV (a documented limit)
    return st.text(
        alphabet=st.characters(blacklist_categories=("Cs", "Cc", "Zs", "Zl", "Zp")), min_size=1, max_size=12
    ).map(lambda t: "t_" + t)


@given(
    st.lists(st.integers(-(2**62), 2**62), min_size=1, max_size=8),
    st.lists(table_text(), min_size=1, max_size=8),
    st.lists(st.booleans(), min_size=1, max_size=8),
)
def table_of_integers_texts_booleans_round_trips(ints, texts, flags):
    n = min(len(ints), len(texts), len(flags))
    frame = pd.DataFrame({"i": ints[:n], "s": texts[:n], "b": flags[:n]})
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "t.csv"
        harness.write_csv(frame, path)
        got = call_loader("echo_table", "table", str(path))["table"]
        assert list(got.columns) == ["i", "s", "b"]
        assert (
            got["i"].tolist() == ints[:n]
            and got["s"].tolist() == texts[:n]
            and got["b"].tolist() == flags[:n]
        )
        results = convert.build_results(TOOLS["echo_table"], (got, {}), folder)
        rows = read_rows(results[0]["path"])
        assert rows[0] == ["i", "s", "b"]
        assert [r[0] for r in rows[1:]] == [str(v) for v in ints[:n]]
        assert [r[1] for r in rows[1:]] == texts[:n]
        assert [r[2] for r in rows[1:]] == [str(v) for v in flags[:n]]


@given(st.lists(FINITE, min_size=1, max_size=20))
def table_floats_survive_the_csv_exactly(values):
    frame = pd.DataFrame({"f": values})
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "t.csv"
        harness.write_csv(frame, path)
        got = call_loader("echo_table", "table", str(path))["table"]["f"].tolist()
        assert all(same(float(g), v) for g, v in zip(got, values)) and len(got) == len(values), (got, values)


@given(st.lists(FINITE, min_size=1, max_size=20))
def table_floats_are_written_exactly(values):
    with tempfile.TemporaryDirectory() as folder:
        results = convert.build_results(
            {"outputs": [{"name": "table", "type": "table"}]}, {"f": values}, folder
        )
        rows = read_rows(results[0]["path"])[1:]
        assert all(same(float(r[0]), v) for r, v in zip(rows, values)) and len(rows) == len(values)


@given(
    st.lists(FINITE, min_size=0, max_size=12),
    st.lists(FINITE, min_size=0, max_size=12),
)
def points_round_trip(ys, xs):
    n = min(len(ys), len(xs))
    with tempfile.TemporaryDirectory() as folder:
        results = convert.build_results(
            {"outputs": [{"name": "points", "type": "points"}]},
            {"y": ys[:n], "x": xs[:n], "label": list(range(n))},
            folder,
        )
        rows = read_rows(results[0]["path"])
        assert rows[0] == ["y", "x", "label"] and results[0]["n"] == n
        assert all(same(float(r[0]), y) and same(float(r[1]), x) for r, y, x in zip(rows[1:], ys, xs))


@given(
    st.lists(st.lists(st.tuples(FINITE, FINITE), min_size=3, max_size=7, unique=True), min_size=0, max_size=4)
)
def polygons_become_closed_geojson_with_x_before_y(polygons):
    with tempfile.TemporaryDirectory() as folder:
        results = convert.build_results(
            {"outputs": [{"name": "shapes", "type": "shapes"}]},
            [[list(v) for v in p] for p in polygons],
            folder,
        )
        collection = json.loads(Path(results[0]["path"]).read_text(encoding="utf-8"))
    expected = [[[float(x), float(y)] for y, x in p] + [[float(p[0][1]), float(p[0][0])]] for p in polygons]
    got = [f["geometry"]["coordinates"][0] for f in collection["features"]]
    assert same(got, expected) and results[0]["n"] == len(polygons), (got, expected)


@given(st.lists(st.lists(FINITE, min_size=3, max_size=3), min_size=3, max_size=3))
def affine_round_trip(matrix):
    with tempfile.TemporaryDirectory() as folder:
        results = convert.build_results({"outputs": [{"name": "affine", "type": "affine"}]}, matrix, folder)
    assert same(results[0]["matrix_yx"], [[float(v) for v in row] for row in matrix])


@given(st.lists(st.lists(FINITE, min_size=3, max_size=3), min_size=2, max_size=2))
def affine_two_by_three_is_completed(matrix):
    with tempfile.TemporaryDirectory() as folder:
        results = convert.build_results({"outputs": [{"name": "affine", "type": "affine"}]}, matrix, folder)
    assert same(results[0]["matrix_yx"], [[float(v) for v in row] for row in matrix] + [[0.0, 0.0, 1.0]])


@given(TEXTS)
def message_is_the_stripped_text(text):
    schema = {"outputs": [{"name": "message", "type": "message"}]}
    with tempfile.TemporaryDirectory() as folder:
        try:
            results = convert.build_results(schema, text, folder)
        except ToolError as error:
            assert text.strip() == "" and error.code == "bad_return"
            return
    assert text.strip() != "" and results[0]["text"] == text.strip()


SAFE_NAME = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc"), blacklist_characters='/\\:*?"<>|\x00%~'),
    min_size=1,
    max_size=30,
).filter(
    lambda n: n == n.strip()
    and not n.endswith(".")
    and n.upper().split(".")[0] not in ("CON", "PRN", "AUX", "NUL", "COM1", "LPT1")
)


@given(SAFE_NAME, st.binary(max_size=64))
def file_path_arrives_unchanged_and_names_the_same_bytes(name, content):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / name
        try:
            path.write_bytes(content)
        except OSError:
            return  # this file system cannot hold that name
        got = call_loader("echo_file", "file", str(path))["file"]
        assert str(got) == str(path) and got.read_bytes() == content
        results = convert.build_results(TOOLS["echo_file"], (got, {}), folder)
        assert results[0]["path"] == str(path)


# -------------------------------------------------------------------------------------------------- JSON safety
NUMPY_LEAVES = st.one_of(
    st.builds(np.float32, st.floats(width=32)),
    st.builds(np.float64, st.floats()),
    st.builds(np.int64, st.integers(-(2**63), 2**63 - 1)),
    st.builds(np.uint8, st.integers(0, 255)),
    st.builds(np.bool_, st.booleans()),
)
SCALAR_VALUES = st.recursive(
    st.none() | st.booleans() | st.integers(-(2**63), 2**63) | st.floats() | TEXTS | NUMPY_LEAVES,
    lambda inner: st.lists(inner, max_size=3)
    | st.tuples(inner, inner)
    | st.dictionaries(TEXTS, inner, max_size=3),
    max_leaves=8,
)


def _refuse_constant(constant):
    raise AssertionError("the constant %s is not JSON" % constant)


def expected_json(value):
    """The value as strict JSON carries it: numpy scalars as Python numbers, NaN and infinity as null, tuples as lists."""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (list, tuple)):
        return [expected_json(v) for v in value]
    if isinstance(value, dict):
        return {str(k): expected_json(v) for k, v in value.items()}
    return value


@given(st.dictionaries(TEXTS, SCALAR_VALUES, max_size=4))
def scalars_results_are_strict_json_with_nan_as_null(values):
    with tempfile.TemporaryDirectory() as folder:
        results = convert.build_results({"outputs": [{"name": "values", "type": "values"}]}, values, folder)
    text = json.dumps(results[0]["values"], allow_nan=False)  # raises if a NaN or infinity got through
    assert same(json.loads(text), expected_json(values))
    line = protocol._encode({"task": "t", "responseType": "COMPLETION", "outputs": {"results": results}})
    json.loads(
        line, parse_constant=lambda c: (_ for _ in ()).throw(AssertionError("non-JSON constant %s" % c))
    )


@given(
    st.dictionaries(
        st.text(max_size=5),
        st.recursive(st.floats() | st.integers(), lambda c: st.lists(c, max_size=3), max_leaves=6),
        max_size=4,
    )
)
def wire_messages_with_non_finite_numbers_are_strict_json(fields):
    line = protocol._encode(
        {"task": "t", "responseType": "UPDATE", **{"f_" + k: v for k, v in fields.items()}}
    )
    json.loads(line, parse_constant=_refuse_constant)


@given(st.sets(st.integers(), min_size=1, max_size=3))
def values_json_cannot_carry_are_refused_never_turned_into_text(items):
    try:
        protocol._encode({"task": "t", "responseType": "COMPLETION", "outputs": {"x": items}})
    except TypeError:
        return
    raise AssertionError("a set was serialised")


# ----------------------------------------------------------- arbitrary text never becomes a path or shell text
@given(TEXTS)
def text_parameter_stays_text_in_the_converter(text):
    out = call_loader("echo_string", "value", text)["value"]
    assert type(out) is str and out == text


@given(TEXTS)
def text_parameter_stays_text_on_the_command_line_parser(text):
    param = TOOLS["echo_string"]["inputs"][0]
    got = cli.parse_value(param, text)
    assert type(got) is str and got == text


@given(SAFE_NAME)
def text_parameter_is_not_resolved_to_a_file_by_the_author_test_harness(name):
    with tempfile.TemporaryDirectory() as folder:
        try:
            (Path(folder) / name).write_text("x", encoding="utf-8")
        except OSError:
            return
        case = {"tool": "echo_string", "inputs": {"value": name}, "_dir": folder}
        inputs = testing._resolve_paths(case, TOOLS["echo_string"])
        assert same(inputs["value"], name)
        file_case = {"tool": "echo_file", "inputs": {"file": name}, "_dir": folder}
        resolved = testing._resolve_paths(file_case, TOOLS["echo_file"])["file"]
        assert (
            Path(resolved) == (Path(folder) / name).resolve()
        )  # a File parameter IS resolved: that is its job


@given(TEXTS.filter(lambda t: "\x00" not in t), TEXTS.filter(lambda t: "\x00" not in t))
def posix_command_line_is_one_word_per_parameter(app, text):
    line = command.command_line(app, TOOLS["echo_string"], {"value": text}, python="python", windows=False)
    assert shlex.split(line) == [
        "python",
        "-m",
        "labconstrictor_tools",
        "run",
        app,
        "echo_string",
        "value=" + text,
    ]


@given(TEXTS.filter(lambda t: "\x00" not in t), TEXTS.filter(lambda t: "\x00" not in t))
def snippet_is_python_that_holds_exactly_the_values(app, text):
    snippet = command.python_snippet(app, TOOLS["echo_string"], {"value": text})
    call = next(
        n
        for n in ast.walk(ast.parse(snippet))
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "run_once"
    )
    assert [ast.literal_eval(a) for a in call.args] == [app, "echo_string", {"value": text}]


@given(TEXTS.filter(lambda t: "\x00" not in t))
def windows_quoting_keeps_a_text_one_argument(text):
    from test_roundtrip_command import parse_windows_command_line

    assert parse_windows_command_line("prog " + command.quote(text, windows=True)) == ["prog", text]


@given(TEXTS.filter(lambda t: "\x00" not in t))
def posix_quoting_is_inverted_by_the_shell_parser(text):
    assert shlex.split(command.quote(text, windows=False)) == [text]


PROPERTIES = {
    name: function
    for name, function in sorted(globals().items())
    if callable(function) and hasattr(function, "hypothesis") and not name.startswith("_")
}


class Properties(unittest.TestCase):
    """One test per property (test_<name>), so that a failure, a sabotage slice or a mutation run names exactly one."""

    def test_there_are_many_properties(self):
        self.assertGreater(len(PROPERTIES), 40)

    def test_profile_is_deterministic_in_ci(self):
        if os.environ.get("LC_HYPOTHESIS_PROFILE", "ci") == "ci":
            self.assertTrue(settings.default.derandomize)
            self.assertEqual(settings.default.max_examples, 200)


def _make_test(name, function):
    def test(self):
        if is_known("property:" + name):
            self.skipTest(
                "known failure %s, watched by test_roundtrip_known_failures" % KNOWN[("property:" + name)]
            )
        function()

    test.__name__ = "test_" + name
    return test


for _name, _function in PROPERTIES.items():
    setattr(Properties, "test_" + _name, _make_test(_name, _function))


def tearDownModule():
    """Release what this module's tests left to the garbage collector now, so that a ResourceWarning for an unclosed pipe is
    raised here and not in whichever test happens to run next (some older tests count ResourceWarnings)."""
    import gc

    gc.collect()


if __name__ == "__main__":
    unittest.main()
