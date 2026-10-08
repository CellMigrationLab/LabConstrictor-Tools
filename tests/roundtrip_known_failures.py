"""Real defects the round-trip tests found in the production code. NOT fixed in the test PR: each finding gets its own fix PR.

`FINDINGS` describes each defect (minimal reproduction, expected correct behaviour, what happens today). `KNOWN` lists the test
ids that fail because of it. Keys are `<transport>:<case id>` for the matrix, `property:<name>` for the hypothesis properties and
`winquote:<label>` for the Windows quoting oracle. The runners skip exactly these ids; test_roundtrip_known_failures.py runs them
again and FAILS when one starts passing, so the PR that fixes a finding has to delete its entries (the list cannot rot).
"""

import functools
import os
import platform
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

META = False  # test_roundtrip_known_failures sets this while it re-runs the listed tests, so that they do not skip themselves


@dataclass(frozen=True)
class Finding:
    title: str
    repro: str  # minimal reproduction
    expected: str  # the correct behaviour
    observed: str  # what happens today
    platforms: tuple[str, ...] = ("posix", "nt")  # os.name values on which the defect shows
    min_python: tuple[int, ...] = (0,)  # the defect shows from this Python version on
    machines: tuple[str, ...] = ()  # platform.machine() values on which it shows (empty: every machine)


SCHEMA = '{"id": "t", "label": "t", "outputs": [], "inputs": [{"name": "n", "label": "N", "type": "%s", "required": True}]}'

FINDINGS: dict[str, Finding] = {
    "F1": Finding(
        "A number parameter given something that is not a number raises a raw Python exception",
        'from labconstrictor_tools import convert\nschema = %s\nconvert.load_inputs(schema, {"n": "abc"})   # ValueError; [1] -> TypeError;'
        ' float("inf") -> OverflowError (type "float": 10**400 -> OverflowError)' % (SCHEMA % "integer"),
        "ToolError('invalid_parameter', \"'N' must be an integer\") (or a number): the host is told FAILURE code invalid_parameter, "
        "as docs/PROTOCOL.md promises for every value-rule violation",
        "FAILURE with the Python exception class as code, e.g. [ValueError] invalid literal for int() with base 10: 'abc'",
    ),
    "F5": Finding(
        "A tool that returns the wrong kind of value for an output gets a raw Python exception, not a ToolError('bad_return')",
        "a tool returns [[1, 0, 0], [0, 1], [0, 0, 1]] (ragged) or [['a', 0, 0], [0, 1, 0], [0, 0, 1]] as its Affine output; or "
        "convert.build_results(schema_with_a_points_output, False, folder); or {} as Affine, None as an image, 5 as Scalars",
        "ToolError('bad_return', '... must be ...') as for a matrix of the wrong shape or a missing y/x column, so the author "
        "gets the same readable failure for every kind of wrong return",
        "FAILURE with the exception class as code: ValueError (inhomogeneous shape / could not convert string to float), "
        "TypeError, ...",
    ),
    "F6": Finding(
        "An Affine output with NaN or infinity is delivered as null instead of being refused",
        "a tool returns [[1, 0, float('nan')], [0, 1, 0], [0, 0, 1]] as its Affine output",
        "ToolError('bad_return', ...) like PointsOut and ShapesOut, and like the author test harness's contract check "
        "('affines are finite 3x3')",
        "COMPLETE with matrix_yx containing null; a host that applies it moves the image to nowhere",
    ),
    "F8": Finding(
        "The notebook form clamps integers and floats beyond 10**9 without telling the person",
        "labconstrictor_tools.notebook.ToolForm(echo_int).controls['value'].value = 2**31; form.run() reports 1000000000",
        "the value is kept (a text box for unbounded numbers) or the form refuses it with a message",
        "BoundedIntText/BoundedFloatText with the made-up limits UNBOUNDED_INT / UNBOUNDED_FLOAT silently change the value",
    ),
    "F9": Finding(
        "The notebook form cannot leave an optional parameter unset",
        "ToolForm(echo_optional_int): run() without touching the control sends 0; the string sends ''; the bool False; the "
        "choice its first option",
        "an unset optional parameter is omitted from the inputs so the tool receives None (docs/PROTOCOL.md: 'showing 0 or an "
        "empty string instead is a bug')",
        "the tool receives 0 / '' / False / the first option: 'unset' cannot be expressed in the notebook",
    ),
    "F10": Finding(
        "command.quote(windows=True) breaks texts with backslashes before a quote",
        'command.quote(\'x y\\\\"z\', windows=True) and command.quote("C:\\\\My Data\\\\", windows=True): parse the result with '
        "CommandLineToArgvW / the MSVC rules (tests/test_roundtrip_command.py has the parser)",
        "the copied Windows command line gives the program exactly the text: backslashes in front of a quote (or of the closing "
        "quote) are doubled",
        "a folder path with a space that ends in a backslash, or a text with backslashes before a double quote, comes out "
        "changed (the closing quote is swallowed)",
    ),
    "F11": Finding(
        "A malformed or stale shared-memory image descriptor raises a raw exception",
        'convert.load_inputs(schema, {"image": {"appose_type": "ndarray"}}) -> KeyError; an unknown "shm" name -> FileNotFoundError',
        "ToolError('unreadable_image', 'the shared-memory image ... is gone or malformed')",
        "FAILURE with code KeyError / FileNotFoundError / TypeError / ValueError",
    ),
    "F12": Finding(
        "A file or folder parameter given a non-text JSON value raises TypeError",
        'convert.load_inputs(schema_with_a_file_parameter, {"f": [1]}) -> TypeError from Path([1])',
        "ToolError('invalid_parameter', 'must be a path (text)')",
        "FAILURE code TypeError",
    ),
    "F14": Finding(
        "labels_to_shapes drops objects that the simplification collapses (a single pixel with the default settings)",
        "import numpy as np; from labconstrictor_tools.shapes import labels_to_shapes\n"
        "a = np.zeros((5, 5), np.uint8); a[2, 2] = 1\nlabels_to_shapes(a)['features']   # [] (default simplify=0.5, min_area=1); "
        "a 1x3 bar is dropped with simplify=1.0",
        "every label with at least min_area pixels has a feature: when the simplified outline degenerates, keep the "
        "unsimplified one (or the simplification is clamped so that it cannot collapse the object)",
        "an empty FeatureCollection for an image of single-pixel objects: the objects exist (count_labels sees them) but nothing "
        "is drawn and nothing says why",
    ),
    "F15": Finding(
        "An image output that no host can open is written (or crashes with KeyError) instead of being refused",
        "a tool declared -> ImageOut returns np.zeros((0, 3), np.uint8) or np.zeros((2, 2), np.complex64) or "
        "np.array([[None, 1]], dtype=object) or np.array([['a', 'b']]) (examples.roundtrip.make_array)",
        "ToolError('bad_return' / 'unsupported_dtype', ...): an empty image is refused on the way in (empty_image) and every "
        "host fails on a complex or text TIFF, so the tool is told at once",
        "empty and complex arrays are written (the empty one as a nonconformant TIFF that the bridge itself refuses to read back); "
        "object and text arrays fail with [KeyError] 'O' / 'U'",
    ),
    "F16": Finding(
        "Hints on the wrong kind of parameter, or with an impossible value, are accepted and silently ignored",
        "Annotated[str, Min(0)], Annotated[int, Min(5), Max(1)], Annotated[str, Axes('YX')], Annotated[int, PixelSizeOf('image')], "
        "Annotated[str, Replace()] (an output marker on an input), two outputs both named with Name('same'): "
        "describe_tool accepts every one of them (tests/test_roundtrip_hints.py generates the full list)",
        "a clear DeclarationError that names the parameter and what to change: docs/MANIFEST.md asks for 'a clear declaration "
        "error for misuse' for every marker; an author who wrote Min on a text parameter or Min(5), Max(1) has made a mistake",
        "the hint disappears from the schema (or an empty range / a renamed output is published): the app registers and the "
        "mistake is found by a person, if at all. (Duplicate explicit output names become 'same' and 'same2': the "
        "'duplicate output names' DeclarationError in introspection._outputs can never be raised)",
    ),
    "F17": Finding(
        "Asking a dead worker for a task raises BrokenPipeError in the host (and leaves the task registered)",
        "w = WorkerProcess(...); w.task('crash', {}).wait(); w.task('echo', {})   # BrokenPipeError: [Errno 32] Broken pipe",
        "a CRASHED task whose message says the worker is gone (with its last words), so every host handles one case, not two",
        "an OSError from WorkerProcess.task(); Task objects stay in worker.tasks for ever",
    ),
    "F18": Finding(
        "On POSIX the processes a tool started survive the worker when the host goes away",
        "start a worker, run a tool that starts a subprocess and keeps running, close the worker's stdin without calling close(): "
        "the worker exits within a second, the tool's subprocess keeps running (tests/test_roundtrip_failures.py::children_problems)",
        "nothing a tool started outlives the worker on any platform: the Windows worker puts its children in a job object, "
        "the POSIX worker should kill its own process group (it leads one) when it leaves after the host went away",
        "orphaned subprocesses (a segmentation or a model server of a tool) keep running after Napari crashed or was killed",
        ("posix",),
    ),
    "F19": Finding(
        "Progress is truncated, not rounded: progress(0.29) is shown as 28 %",
        "progress(0.29, 'x') in a tool; the host's callback receives 0.28 (also 0.57 -> 0.56, 0.58 -> 0.57)",
        "the whole percent nearest to the fraction (round(100 * fraction)), as the tool reported it",
        "int(100 * fraction) in worker._send_progress loses a percent whenever 100 * fraction is just below the integer",
    ),
    "F20": Finding(
        "Integer images are checked for float32 exactness with an out-of-range cast: uint64 2**64-1 is stored as 2**64 on ARM",
        "from labconstrictor_tools.convert import portable_dtype; import numpy as np\n"
        "portable_dtype(np.array([[2**64 - 1, 1]], np.uint64))   # x86: ToolError unsupported_dtype; arm64 (Apple silicon): a float32 array holding 2**64",
        "ToolError('unsupported_dtype', ...) on every machine: 2**64-1 is not exactly representable as float32 (docs/PROTOCOL.md: integers never change in value)",
        "convert.portable_dtype tests exactness with np.array_equal(widened.astype(array.dtype), array); casting the float32 2**64 back to uint64 is "
        "undefined: x86 gives 0 (not equal, refused), ARM saturates to 2**64-1 (equal, accepted) so the value is silently changed by 1. "
        "Seen on GitHub's macOS runners (arm64); not reproducible on x86 Linux",
        ("posix", "nt"),
        (0,),
        ("arm64", "aarch64"),
    ),
    "F13": Finding(
        "The worker destroys the host's shared-memory block when it exits",
        "the host creates a block, sends it as an image input, the task completes, the worker is closed: the block is gone, and the "
        "worker's stderr holds 'resource_tracker: There appear to be 1 leaked shared_memory objects' (tests/test_roundtrip_shared_memory.py)",
        "the worker only maps the block: the host that created it unlinks it when it is done "
        "(unregister it from the worker's resource tracker after attaching, or SharedMemory(track=False) on Python 3.13+)",
        "Python's resource tracker in the worker unlinks every block it attached to when the worker exits, so a host that "
        "keeps a block between tasks (or reuses it after a worker restart) finds it gone, and the warning ends up in crash messages",
        ("posix",),
    ),
}

KNOWN: dict[str, str] = {}


def _add(finding: str, *keys: str) -> None:
    for key in keys:
        KNOWN[key] = finding


_add(
    "F1",
    "worker:echo_float/dict",
    "worker:echo_float/empty-text",
    "worker:echo_float/huge-int",
    "worker:echo_float/list",
    "worker:echo_float/word",
    "worker:echo_int/decimal-text",
    "worker:echo_int/dict",
    "worker:echo_int/empty-text",
    "worker:echo_int/inf",
    "worker:echo_int/list",
    "worker:echo_int/minus-inf",
    "worker:echo_int/nan",
    "worker:echo_int/word",
    "property:only_toolerror_integer",
    "property:only_toolerror_float",
    "property:only_toolerror_bounded",
)
_add(
    "F5",
    "property:only_toolerror_result_affine",
    "property:only_toolerror_result_image",
    "property:only_toolerror_result_points",
    "property:only_toolerror_result_table",
    "property:only_toolerror_result_values",
    "failure:wrong_type_image",
    "failure:wrong_type_table",
    "failure:wrong_type_scalars",
    "failure:wrong_type_points",
    "failure:wrong_count_one_array",
    "failure:wrong_count_tuple_for_one",
    "worker:echo_affine/invalid/ragged",
    "worker:echo_affine/invalid/text-cell",
)
_add(
    "F6",
    "worker:echo_affine/invalid/inf-cell",
    "worker:echo_affine/invalid/nan-cell",
)
_add(
    "F8",
    "notebook:echo_float/ok/0x1.c6bf526340000p+49",
    "notebook:echo_int/ok/-2147483648",
    "notebook:echo_int/ok/2147483647",
    "notebook:echo_int/ok/2147483648",
    "notebook:echo_optional_int/set/1099511627776",
)
_add(
    "F9",
    "notebook:echo_optional_bool/omitted",
    "notebook:echo_optional_choice/omitted",
    "notebook:echo_optional_float/omitted",
    "notebook:echo_optional_int/omitted",
    "notebook:echo_optional_string/omitted",
)
_add(
    "F10",
    "winquote:quote-after-backslashes",
    "winquote:spaced-trailing-backslash",
    "winquote:spaced-quote-after-backslash",
    "property:windows_quoting_keeps_a_text_one_argument",
)
_add(
    "F11",
    "property:only_toolerror_image_shared_memory",
)
_add(
    "F15",
    "worker:make_array/empty",
    "worker:make_array/complex",
    "worker:make_array/object",
    "worker:make_array/text",
)
_add(
    "F20",
    "worker:echo_image/uint64/beyond-float32",
    "cli:echo_image/uint64/beyond-float32",
    "terminal:echo_image/uint64/beyond-float32",
    "snippet:echo_image/uint64/beyond-float32",
    "notebook:echo_image/uint64/beyond-float32",
)
_add(
    "F10",
    "winproc:quote-after-backslashes",
    "winproc:spaced-trailing-backslash",
    "winproc:spaced-quote-after-backslash",
)
_add("F13", "lifecycle:shared_memory_survives_the_worker")
_add("F17", "lifecycle:task_on_a_dead_worker")
_add("F18", "lifecycle:children_die_when_the_host_goes_away")
_add("F19", "lifecycle:progress_percent_is_rounded")
_add(
    "F14",
    "test:test_roundtrip_geometry.Outlines.test_default_simplification_never_drops_a_label",
    "worker:outline_labels/single-pixel-default-simplify",
)
_add(
    "F12",
    "property:only_toolerror_file_value",
    "property:only_toolerror_folder_value",
)
_add(
    "F16",
    "hint:ApplyTo-on-the-input-image",
    "hint:ApplyTo-on-the-input-str",
    "hint:Axes-on-file",
    "hint:Axes-on-int",
    "hint:Axes-on-str",
    "hint:Axes-on-table",
    "hint:Max-on-bool",
    "hint:Max-on-file",
    "hint:Max-on-image",
    "hint:Max-on-literal3",
    "hint:Max-on-str",
    "hint:Min-above-Max",
    "hint:Min-is-not-a-number",
    "hint:Min-on-bool",
    "hint:Min-on-file",
    "hint:Min-on-image",
    "hint:Min-on-literal3",
    "hint:Min-on-str",
    "hint:Name-on-the-input-image",
    "hint:Name-on-the-input-str",
    "hint:PixelSizeOf-on-bool",
    "hint:PixelSizeOf-on-int",
    "hint:PixelSizeOf-on-str",
    "hint:Replace-on-the-input-image",
    "hint:Replace-on-the-input-str",
    "hint:duplicate-output-names",
)


def is_known(key: str) -> bool:
    """True when `key` is a listed failure on this platform (the runners skip it)."""
    finding = KNOWN.get(key)
    if finding is None:
        return False
    f = FINDINGS[finding]
    return (
        os.name in f.platforms
        and sys.version_info[: len(f.min_python)] >= f.min_python
        and (not f.machines or platform.machine().lower() in f.machines)
    )


def known_failure(key: str) -> Callable[[Any], Any]:
    """Decorator of a test method that currently fails because of a listed defect: it skips itself (and says why)."""

    def wrap(test: Any) -> Any:
        @functools.wraps(test)
        def run(self: Any, *args: Any, **kwargs: Any) -> Any:
            if is_known(key) and not META:
                self.skipTest("known failure %s, watched by test_roundtrip_known_failures" % KNOWN[key])
            return test(self, *args, **kwargs)

        return run

    return wrap
