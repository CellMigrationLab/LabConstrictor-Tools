"""Do the round-trip tests have teeth? For each production function in the table below, copy the package and the tests to a
temporary tree, apply ONE deliberate break (flip a comparison, swap x and y, drop a case, ...), run the slice of the matrix that is
meant to guard that function against the broken copy in a subprocess, and require it to FAIL. A break that survives fails this
test and is named: the matrix is missing a case for it.

Every slice is run first on the unbroken copy and must pass there (otherwise a red result would prove nothing). The package is
broken in the temporary tree only; nothing in the repository is touched. Linux only (about a minute and a half; the same slices
run everywhere as ordinary tests).
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

PARALLEL = 4
SLICE_TIMEOUT_S = 240
ONLY = os.environ.get("LC_SABOTAGE_ONLY")  # a regular expression on break ids, for working on one break


@dataclass(frozen=True)
class Slice:
    """A command that runs part of the tests (`unittest` arguments) with environment filters."""

    name: str
    arguments: tuple[str, ...]
    env: tuple[tuple[str, str], ...] = ()


def matrix(filter_regex: str, test: str = "test_worker_protocol") -> Slice:
    return Slice(
        "matrix %s /%s/" % (test, filter_regex),
        ("test_roundtrip_matrix.Matrix." + test,),
        (("LC_ROUNDTRIP_FILTER", filter_regex),),
    )


def properties(name: str) -> Slice:
    return Slice("property %s" % name, ("test_roundtrip_properties.Properties.test_" + name,))


def unittest_slice(*arguments: str) -> Slice:
    return Slice(" ".join(arguments), tuple(arguments))


@dataclass(frozen=True)
class Break:
    id: str
    file: str  # relative to the package
    old: str
    new: str
    guard: Slice
    why: str = ""
    count: int = 1  # how often `old` occurs; the first occurrence is broken when it is more than 1


BREAKS = [
    # ---- converters
    Break(
        "convert: lower bound is exclusive",
        "convert.py",
        'value < param["minimum"]',
        'value <= param["minimum"]',
        matrix("echo_bounded_int/ok/-5|echo_bounded_float/ok/-0.5|echo_slider_int/ok/0"),
    ),
    Break(
        "convert: upper bound is exclusive",
        "convert.py",
        'value > param["maximum"]',
        'value >= param["maximum"]',
        matrix("echo_bounded_int/ok/10|echo_max_only/ok/100"),
    ),
    Break(
        "convert: a boolean is accepted as an integer",
        "convert.py",
        "return isinstance(value, (int, float)) and not isinstance(value, bool)",
        "return isinstance(value, (int, float))",
        matrix("echo_int/bool"),
    ),
    Break(
        "convert: a fraction is accepted as an integer",
        "convert.py",
        "if isinstance(value, float) and not (math.isfinite(value) and value.is_integer()):",
        "if False:",
        matrix("echo_int/(fraction|tiny)"),
    ),
    Break(
        "convert: text is guessed to be a boolean",
        "convert.py",
        "if not isinstance(value, bool):  # bool",
        "if False:  # bool",
        matrix("echo_bool/(text|one|zero)"),
    ),
    Break(
        "convert: 1 is accepted for True (type not compared)",
        "convert.py",
        "type(value) is type(c) and value == c for c in param",
        "value == c for c in param",
        matrix("echo_number_choice/invalid|echo_choice/invalid"),
    ),
    Break(
        "convert: NaN and infinity accepted as floats",
        "convert.py",
        "if not math.isfinite(number):",
        "if False:",
        matrix("echo_float/(nan|inf|minus-inf)"),
    ),
    Break(
        "convert: an unset parameter becomes 0",
        "convert.py",
        'kwargs[name] = param.get("default")',
        'kwargs[name] = param.get("default", 0)',
        matrix("echo_optional_int/omitted|echo_optional_string/omitted"),
    ),
    Break(
        "convert: an Enum reaches the tool as its value",
        "convert.py",
        "kwargs[name] = base(value)",
        "kwargs[name] = value",
        matrix("echo_enum/ok"),
    ),
    Break(
        "convert: a File arrives as text",
        "convert.py",
        '        return _path_text(param["label"], value)\n    if kind == "folder":',
        '        return str(value)\n    if kind == "folder":',
        matrix("echo_file/name/plain"),
    ),
    Break(
        "convert: a boolean image is not turned into bytes",
        "convert.py",
        "return array.astype(np.uint8)",
        "return array",
        matrix("echo_image/bool/2x3"),
    ),
    Break(
        "convert: 65536 is stored as 16-bit",
        "convert.py",
        "65535  # integer images",
        "65536  # integer images",
        matrix("echo_image/int32/just-beyond"),
    ),
    Break(
        "convert: float64 beyond float32 is not refused",
        "convert.py",
        "if np.any(np.isinf(narrowed) & np.isfinite(array)):",
        "if False:",
        matrix("echo_image/float64/beyond"),
    ),
    Break(
        "convert: points come out as x, y",
        "convert.py",
        'frame = frame[["y", "x"] + others]',
        'frame = frame[["x", "y"] + others]',
        matrix("echo_points/x-before-y|grid_points/2x3"),
    ),
    Break(
        "convert: polygon vertices are not swapped to [x, y]",
        "convert.py",
        "ring = [[float(x), float(y)] for y, x in array]",
        "ring = [[float(y), float(x)] for y, x in array]",
        matrix("echo_polygons/(triangle|yx)"),
    ),
    Break(
        "convert: polygon rings are not closed",
        "convert.py",
        "return ring + [ring[0]]",
        "return ring",
        matrix("echo_polygons/triangle"),
    ),
    Break(
        "convert: a 2x3 affine is not completed correctly",
        "convert.py",
        "np.vstack([m, [0, 0, 1]])",
        "np.vstack([m, [0, 0, 0]])",
        matrix("echo_affine/two-by-three"),
    ),
    Break(
        "convert: a message is not stripped",
        "convert.py",
        "text = value.strip()",
        "text = value",
        matrix("echo_message/surrounded"),
    ),
    Break(
        "convert: NaN stays a number in the results",
        "convert.py",
        "    if isinstance(value, float) and not math.isfinite(value):\n        return None",
        "    if False:\n        return None",
        properties("scalars_results_are_strict_json_with_nan_as_null"),
    ),
    Break(
        "convert: the number of returned values is not checked",
        "convert.py",
        "if len(outputs) != len(values):",
        "if False:",
        unittest_slice(
            "test_roundtrip_failures.WhatAToolReturns.test_the_wrong_number_of_values_is_bad_return_with_both_counts"
        ),
    ),
    # ---- protocol and worker
    Break(
        "protocol: NaN is sent as the NaN constant",
        "protocol.py",
        "return json.dumps(_finite(message), allow_nan=False)",
        "return json.dumps(message)",
        properties("wire_messages_with_non_finite_numbers_are_strict_json"),
    ),
    Break(
        "worker: the code is dropped from a ToolError message",
        "worker.py",
        '"error": "[%s] %s" % (error.code, error.message), "code": error.code',
        '"error": error.message, "code": error.code',
        unittest_slice(
            "test_roundtrip_failures.WhatAToolRaises.test_a_tool_error_arrives_with_its_code_and_text"
        ),
    ),
    Break(
        "worker: sys.exit() is reported as another exception",
        "worker.py",
        '"code": type(error).__name__,',
        '"code": "Exception",',
        unittest_slice(
            "test_roundtrip_failures.WhatAToolRaises.test_memory_error_and_exits_do_not_take_the_worker_down"
        ),
        count=2,
    ),
    Break(
        "worker: progress is off by one percent",
        "worker.py",
        "math.floor(PROGRESS_MAXIMUM * fraction + PROGRESS_HALF)",
        "math.floor(PROGRESS_MAXIMUM * fraction + PROGRESS_HALF) + 1",
        unittest_slice("test_roundtrip_failures.WhatAToolReturns.test_every_whole_percent_arrives_as_itself"),
    ),
    Break(
        "worker: the inputs are not passed to the tool",
        "worker.py",
        "kwargs = convert.load_inputs(schema, inputs, self.tools[tool_id].fn)",
        "kwargs = convert.load_inputs(schema, {}, self.tools[tool_id].fn)",
        matrix("echo_bool/ok|echo_string/text/emoji"),
    ),
    # ---- client
    Break(
        "client: a failure is reported as a crash",
        "client.py",
        '"FAILURE": "FAILED",',
        '"FAILURE": "CRASHED",',
        unittest_slice(
            "test_roundtrip_failures.WhatAToolRaises.test_a_tool_error_arrives_with_its_code_and_text".replace(
                "Tooo", "Too"
            )
        ),
    ),
    Break(
        "client: a crash loses its exit code",
        "client.py",
        'message = "worker exited unexpectedly (code %s)" % returncode',
        'message = "worker exited unexpectedly"',
        unittest_slice(
            "test_roundtrip_failures.Crashes.test_a_worker_that_exits_mid_task_gives_crashed_with_its_exit_code"
        ),
    ),
    # ---- introspection (validators)
    Break(
        "introspection: Optional[...] is not nullable",
        "introspection.py",
        "ann, optional = a[0], True",
        "ann, optional = a[0], False",
        unittest_slice("test_roundtrip_hints.ValidCombinations", "test_roundtrip_hints.TheValidatorHasTeeth"),
    ),
    Break(
        "introspection: defaults are not checked",
        "introspection.py",
        "if ok and not ok(value):",
        "if False:",
        unittest_slice("test_roundtrip_hints.InvalidCombinations"),
    ),
    Break(
        "introspection: radio accepts 1 to 9 choices",
        "introspection.py",
        '2 <= len(d["choices"]) <= 5',
        '1 <= len(d["choices"]) <= 9',
        unittest_slice("test_roundtrip_hints.InvalidCombinations"),
    ),
    Break(
        "introspection: a slider needs no bounds",
        "introspection.py",
        'or "minimum" not in d or "maximum" not in d',
        "or False",
        unittest_slice("test_roundtrip_hints.InvalidCombinations"),
    ),
    # ---- the quoting helper and the copied text
    Break(
        "command: POSIX quoting removed",
        "command.py",
        "return shlex.quote(text)",
        "return text",
        unittest_slice("test_roundtrip_command.QuotingHelper.test_posix_quoting_survives_a_real_shell"),
    ),
    Break(
        "command: Windows quoting loses the double quotes",
        "command.py",
        "text.replace('\"', '\\\\\"')",
        "text.replace('\"', '')",
        unittest_slice(
            "test_roundtrip_command.QuotingHelper.test_windows_quoting_keeps_every_text_one_argument"
        ),
    ),
    Break(
        "command: booleans are written as True/False",
        "command.py",
        'return "true" if value else "false"',
        "return str(value)",
        unittest_slice("test_roundtrip_command.CopiedText"),
    ),
    Break(
        "command: the snippet writes values with str, not repr",
        "command.py",
        '"    %r: %r,\\n" % (p["name"], v)',
        '"    %r: %s,\\n" % (p["name"], v)',
        properties("snippet_is_python_that_holds_exactly_the_values"),
    ),
    # ---- geometry
    Break(
        "shapes: outlines come out as [y, x]",
        "shapes.py",
        "[float(c) - 1.0, float(r) - 1.0] for r, c in contour",
        "[float(r) - 1.0, float(c) - 1.0] for r, c in contour",
        unittest_slice("test_roundtrip_geometry.Outlines", "-k", "rasterised_back"),
    ),
    Break(
        "shapes: the half pixel is lost",
        "shapes.py",
        "[float(c) - 1.0, float(r) - 1.0] for r, c in contour",
        "[float(c) - 0.5, float(r) - 0.5] for r, c in contour",
        unittest_slice("test_roundtrip_geometry.Outlines", "-k", "rasterised_back"),
    ),
    Break(
        "shapes: holes are dropped",
        "shapes.py",
        "if owners:  # the smallest",
        "if False:  # the smallest",
        unittest_slice("test_roundtrip_geometry.Outlines", "-k", "hole"),
    ),
    Break(
        "shapes: min_area is exclusive",
        "shapes.py",
        "if area < min_area:",
        "if area <= min_area:",
        unittest_slice("test_roundtrip_geometry.Outlines", "-k", "min_area"),
    ),
    Break(
        "shapes: the crop offset is applied as (x, y)",
        "shapes.py",
        "dy, dx = region[0].start, region[1].start",
        "dx, dy = region[0].start, region[1].start",
        unittest_slice("test_roundtrip_geometry.Outlines", "-k", "translating"),
    ),
    Break(
        "region: the box is one row and column short",
        "region.py",
        "slice(int(rows.min()), int(rows.max()) + 1), slice(int(columns.min()), int(columns.max()) + 1)",
        "slice(int(rows.min()), int(rows.max())), slice(int(columns.min()), int(columns.max()))",
        unittest_slice("test_roundtrip_geometry.RegionBox"),
    ),
    Break(
        "region: rows and columns are swapped",
        "region.py",
        "return slice(int(rows.min()), int(rows.max()) + 1), slice(int(columns.min()), int(columns.max()) + 1)",
        "return slice(int(columns.min()), int(columns.max()) + 1), slice(int(rows.min()), int(rows.max()) + 1)",
        matrix("region_box/(rectangle|two-far)"),
    ),
    Break(
        "region: the size of the mask is not compared with the image",
        "region.py",
        "if image is not None and tuple(array.shape) != tuple(np.asarray(image).shape[-2:]):",
        "if False:",
        matrix("region_box/(wrong-size|3d)"),
    ),
]


def build_tree(destination: Path) -> Path:
    """A private copy of the package and the tests (python files only): `_paths` finds the root next to the tests."""
    shutil.copytree(
        ROOT / "labconstrictor_tools",
        destination / "labconstrictor_tools",
        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"),
    )
    tests = destination / "tests"
    tests.mkdir()
    for path in (ROOT / "tests").glob("*.py"):
        shutil.copy2(path, tests / path.name)
    shutil.copytree(
        ROOT / "tests" / "failure_app", tests / "failure_app", ignore=shutil.ignore_patterns("__pycache__")
    )
    (destination / "pyproject.toml").write_text(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return destination


def apply(break_: Break, tree: Path) -> None:
    path = tree / "labconstrictor_tools" / break_.file
    text = path.read_text(encoding="utf-8")
    found = text.count(break_.old)
    if found != break_.count:
        raise AssertionError(
            "the break %r no longer applies: %r occurs %d times in %s (expected %d); update the table"
            % (break_.id, break_.old, found, break_.file, break_.count)
        )
    path.write_text(text.replace(break_.old, break_.new, 1), encoding="utf-8")
    compile(
        path.read_text(encoding="utf-8"), str(path), "exec"
    )  # a break must be valid Python, or "it failed" proves nothing


def run_slice(tree: Path, guard: Slice) -> subprocess.CompletedProcess:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("PYTHONPATH", "LC_HOME", "COVERAGE_PROCESS_START", "COVERAGE_RCFILE")
    }
    env.update(dict(guard.env))
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "LC_HYPOTHESIS_PROFILE": "ci"})
    return subprocess.run(
        [sys.executable, "-m", "unittest", *guard.arguments],
        cwd=tree / "tests", env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=SLICE_TIMEOUT_S,
    )  # fmt: skip


@unittest.skipUnless(sys.platform.startswith("linux"), "the sabotage run is part of the Linux CI job")
class Sabotage(unittest.TestCase):
    def test_every_break_is_caught(self):
        chosen = [b for b in BREAKS if not ONLY or re.search(ONLY, b.id)]
        ids = [b.id for b in BREAKS]
        self.assertEqual(len(ids), len(set(ids)), "break ids must be unique")
        self.assertGreaterEqual(len(BREAKS), 40)
        with tempfile.TemporaryDirectory(prefix="lc_sabotage_") as folder:
            base = Path(folder)
            controls = {}  # slice -> a pass on the unbroken copy
            unbroken = build_tree(base / "unbroken")
            where = subprocess.run(
                [sys.executable, "-c", "import _paths, labconstrictor_tools; print(labconstrictor_tools.__file__)"],
                cwd=unbroken / "tests", capture_output=True, text=True, timeout=120,
            )  # fmt: skip
            self.assertTrue(
                Path(where.stdout.strip()).resolve().is_relative_to(unbroken.resolve()),
                "the copy must import itself: " + where.stdout + where.stderr,
            )
            slices = sorted({b.guard for b in chosen}, key=lambda s: s.name)
            with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
                for guard, done in zip(slices, pool.map(lambda g: run_slice(unbroken, g), slices)):
                    controls[guard] = done
            for guard, done in controls.items():
                self.assertEqual(
                    done.returncode,
                    0,
                    "the guard %r fails on the UNBROKEN copy, so it proves nothing:\n%s"
                    % (guard.name, (done.stderr + done.stdout)[-3000:]),
                )

            def attempt(index_break):
                index, break_ = index_break
                tree = build_tree(base / ("break%d" % index))
                apply(break_, tree)
                return break_, run_slice(tree, break_.guard)

            with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
                outcomes = list(pool.map(attempt, enumerate(chosen)))
        survivors, dishonest = [], []
        for break_, done in outcomes:
            output = done.stderr + done.stdout
            if done.returncode == 0:
                survivors.append(break_.id)
            elif not re.search(r"FAILED \((failures|errors)", output) or "Ran 0 tests" in output:
                dishonest.append(
                    "%s: the guard did not fail by an assertion:\n%s" % (break_.id, output[-800:])
                )
        if os.environ.get("LC_SABOTAGE_VERBOSE"):
            for break_, done in outcomes:
                print(
                    "%-8s %s   [guard: %s]"
                    % ("SURVIVED" if done.returncode == 0 else "caught", break_.id, break_.guard.name)
                )
        self.assertEqual(dishonest, [])
        self.assertEqual(
            survivors,
            [],
            "these deliberate breaks of production code were NOT caught by the matrix: add a case for each",
        )


class TheTableIsHonest(unittest.TestCase):
    """Runs everywhere and quickly: every break still applies to the source and is valid Python."""

    def test_every_break_applies_to_the_current_source_and_compiles(self):
        with tempfile.TemporaryDirectory(prefix="lc_sabotage_table_") as folder:
            for index, break_ in enumerate(BREAKS):
                with self.subTest(break_.id):
                    tree = Path(folder) / ("t%d" % index)
                    (tree / "labconstrictor_tools").mkdir(parents=True)
                    shutil.copy2(
                        ROOT / "labconstrictor_tools" / break_.file,
                        tree / "labconstrictor_tools" / break_.file,
                    )
                    apply(break_, tree)
                    self.assertNotEqual(break_.old, break_.new)

    def test_the_table_names_a_guard_for_each_family_the_task_lists(self):
        files = {b.file for b in BREAKS}
        self.assertTrue(
            {
                "convert.py",
                "introspection.py",
                "command.py",
                "shapes.py",
                "region.py",
                "worker.py",
                "client.py",
                "protocol.py",
            }
            <= files
        )


if __name__ == "__main__":
    unittest.main()
