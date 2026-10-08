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
    "F2": Finding(
        "A table input does not read floating point cells exactly",
        'a CSV file "f\\n0.30000000000000004\\n" given to a Table parameter: convert.load_inputs(schema, {"t": path})["t"]["f"][0]'
        " is 0.3 (and 6.4575963826141304e+16 is read as 6.45759638261413e+16)",
        "the cell equals float('0.30000000000000004'): pd.read_csv(path, float_precision='round_trip') in convert._load_one",
        "pandas' default C parser rounds the last digit; the tool computes with a different number than the host wrote, and a "
        "TableOut echo then writes the rounded value back",
    ),
    "F3": Finding(
        "Duplicate and empty column names of a table input are renamed silently",
        'a CSV whose header is "a,a" (or ",b"): the tool receives the columns ["a", "a.1"] (["Unnamed: 0", "b"])',
        "the tool sees the names the host wrote, or the call fails with a message that names the problem",
        "pd.read_csv mangles the header; nothing tells the person",
    ),
    "F4": Finding(
        "A table that cannot be read raises a raw pandas/OS exception instead of a ToolError",
        "a missing file, an empty file or binary garbage given to a Table parameter: FileNotFoundError / EmptyDataError / "
        "UnicodeDecodeError",
        "ToolError('file_not_found', ...) for a missing file (like image: file_not_found) and ToolError('unreadable_table', ...) "
        "for content that is not a CSV, so the host shows a readable message",
        "FAILURE with code FileNotFoundError / EmptyDataError / UnicodeDecodeError",
    ),
    "F7": Finding(
        "Text cells that pandas treats as missing (NA, null, None, N/A, nan, ...) arrive as NaN",
        'a CSV column holding the texts "NA", "null", "None": the tool receives NaN for every one of them',
        "a text cell stays text (pd.read_csv(..., keep_default_na=False) and an empty cell as missing), or the behaviour is "
        "documented in docs/PROTOCOL.md",
        "silent loss of the cell's content (a gene called NA, a status 'None')",
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
}

KNOWN: dict[str, str] = {}


def _add(finding: str, *keys: str) -> None:
    for key in keys:
        KNOWN[key] = finding


_add(
    "F2",
    "cli:echo_table/float-digits",
    "cli:echo_table/random-floats",
    "notebook:echo_table/float-digits",
    "notebook:echo_table/random-floats",
    "snippet:echo_table/float-digits",
    "snippet:echo_table/random-floats",
    "terminal:echo_table/float-digits",
    "terminal:echo_table/random-floats",
    "worker:echo_table/float-digits",
    "worker:echo_table/random-floats",
    "property:table_floats_survive_the_csv_exactly",
)
_add(
    "F3",
    "worker:echo_table/duplicate-column-names",
    "worker:echo_table/empty-column-name",
)
_add(
    "F4",
    "cli:echo_table/missing-file",
    "cli:echo_table/no-header-no-rows",
    "terminal:echo_table/missing-file",
    "terminal:echo_table/no-header-no-rows",
    "worker:echo_table/binary-garbage",
    "worker:echo_table/missing-file",
    "worker:echo_table/no-header-no-rows",
    "property:only_toolerror_table_file",
)
_add(
    "F7",
    "cli:echo_table/text-that-pandas-calls-missing",
    "notebook:echo_table/text-that-pandas-calls-missing",
    "snippet:echo_table/text-that-pandas-calls-missing",
    "terminal:echo_table/text-that-pandas-calls-missing",
    "worker:echo_table/text-that-pandas-calls-missing",
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
    "F10",
    "winproc:quote-after-backslashes",
    "winproc:spaced-trailing-backslash",
    "winproc:spaced-quote-after-backslash",
)
_add(
    "F14",
    "test:test_roundtrip_geometry.Outlines.test_default_simplification_never_drops_a_label",
    "worker:outline_labels/single-pixel-default-simplify",
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
