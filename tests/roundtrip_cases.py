"""The round-trip case matrix: plain data, generated, no test logic and no production code.

A `Case` says which tool of `labconstrictor_tools.examples.roundtrip` to call, which HOST-SIDE values to send, and what must
come back. Every expectation is an ORACLE: it is worked out here from the inputs with plain Python and numpy (hashlib, int,
float, np.unique, ...), never by calling the converters under test. A new type or edge value is covered by adding a row to a
generator below; every runner (worker protocol, command line, copied command, notebook form) walks the same list.

Host-side values (what a host holds before it talks to the worker) are: Python scalars and None, numpy arrays (written as TIFF
by the runner), `Shm` (an array handed over in shared memory), pandas DataFrames (written as CSV), `FileSpec`, `FolderSpec`,
`MissingPath`, `JsonFile`. Expected results are `Out*` objects compared by tests/roundtrip_harness.py.

`heavy=True` cases (big arrays, files, tables, texts) run only in the nightly profile (LC_ROUNDTRIP_PROFILE=nightly).
"""

from __future__ import annotations

import functools
import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

APP_MODULE = "labconstrictor_tools.examples.roundtrip"
RNG_SEED = 20261008

# ---------------------------------------------------------------------------------------------- host-side values


@dataclass(frozen=True)
class Shm:
    """An array the host hands over in shared memory (the Appose ndarray descriptor) instead of a TIFF file."""

    array: Any


@dataclass(frozen=True)
class FileSpec:
    """A file the host creates (name, bytes) and sends by path."""

    name: str
    data: bytes


@dataclass(frozen=True)
class FolderSpec:
    name: str
    entries: tuple[tuple[str, bytes], ...] = ()


@dataclass(frozen=True)
class MissingPath:
    """A path that does not exist (`name` is joined to the case's folder, nothing is created)."""

    name: str


@dataclass(frozen=True)
class JsonFile:
    """A file holding `payload` as JSON text (NaN and Infinity allowed in it, as Python's json writes them)."""

    name: str
    payload: Any


@dataclass(frozen=True)
class SentPath:
    """In an expectation: the path (text) the runner actually sent for this parameter."""

    param: str


# ------------------------------------------------------------------------------------------------- expectations


@dataclass(frozen=True)
class OutImage:
    values: Any  # numpy array: the values the host must read back (shape included)
    dtypes: tuple[str, ...]  # the dtypes that are acceptable for them


@dataclass(frozen=True)
class OutTable:
    columns: list[str]
    columns_data: dict[str, list[Any]]  # column name (position-wise) -> cells, NaN as None


@dataclass(frozen=True)
class OutText:
    text: str


@dataclass(frozen=True)
class OutFile:
    digest: str | None = (
        None  # sha256 of the file the result names (None: only that the path is the one sent)
    )
    same_path_as: str | None = None  # name of the input whose path must come back


@dataclass(frozen=True)
class OutPoints:
    columns: list[str]
    columns_data: dict[str, list[Any]]


@dataclass(frozen=True)
class OutShapes:
    collection: dict[str, Any]


@dataclass(frozen=True)
class OutOutlines:
    """Outlines of a label image: the features rasterised back (even-odd rule, pixel centres at integers) must give each
    label's mask again, with the `label` and `area` properties of the labels that have at least `min_area` pixels.
    With `simplify` > 0 the outline may move by that many pixels: the rasterised mask may differ in at most `slack` pixels.
    """

    labels: Any
    min_area: int = 1
    simplify: float = 0.0
    slack: int = 0


@dataclass(frozen=True)
class OutAffine:
    matrix: list[list[float]]
    display: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Expect:
    status: str = "COMPLETE"  # COMPLETE | FAILED
    code: str | None = None  # FAILED: the ToolError code the person is told
    toolerror: bool = False  # FAILED: the code must be a ToolError code, not the name of a Python exception
    message: str | None = None  # FAILED: this text is in the message
    received: dict[str, Any] | None = (
        None  # keys of the tool's report (or of its `values`) that must match exactly
    )
    outputs: dict[str, Any] = field(default_factory=dict)  # output name -> Out*


@dataclass(frozen=True)
class Case:
    id: str
    tool: str
    send: dict[str, Any]
    expect: Expect
    paths: tuple[str, ...] = ("worker",)  # which transports can carry it: worker, cli, snippet, notebook
    heavy: bool = False
    group: str = ""  # the type or hint family, for coverage accounting


# ---------------------------------------------------------------------------------------------------- oracles


def scalar_report(value: Any) -> dict[str, Any]:
    """What an echo tool must report for a received scalar: value, exact Python type, repr, float bits, code points."""
    report: dict[str, Any] = {"value": value, "type": type(value).__name__, "repr": repr(value)}
    if isinstance(value, float):
        report["hex"] = value.hex()
    if isinstance(value, str):
        report["codepoints"] = [ord(c) for c in value]
    return report


def array_report(a: Any) -> dict[str, Any]:
    """dtype, shape and a digest of the logical content (C order) of an array the tool received."""
    a = np.asarray(a)
    report: dict[str, Any] = {
        "dtype": str(a.dtype),
        "shape": list(a.shape),
        "digest": hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest(),
    }
    if a.dtype.kind == "f":
        report["n_nan"] = int(np.isnan(a).sum())
        report["n_inf"] = int(np.isinf(a).sum())
    return report


def _exact_in_float32(value: int) -> bool:
    return int(np.float32(value)) == value


def expected_image_out(a: np.ndarray) -> OutImage | None:
    """What a host reads back for an image/labels output (docs/PROTOCOL.md): booleans as 0/1 bytes; integers never change
    value (16-bit ones stay, wide ones that fit 16 bits are stored as 16-bit, the rest must be exact in float32 or the
    call fails); floats become float32 (a finite value outside its range fails). None means "the call must fail".
    """
    kind = a.dtype.kind
    if kind == "b":
        return OutImage(a.astype(np.uint8), ("uint8",))
    if kind == "f":
        if a.dtype == np.float32:
            return OutImage(a, ("float32",))
        with np.errstate(over="ignore"):
            narrowed = a.astype(np.float32)
        if bool((np.isinf(narrowed) & np.isfinite(a)).any()):
            return None
        return OutImage(narrowed, ("float32",))
    if a.dtype in (np.uint8, np.uint16, np.int16):
        return OutImage(a, (str(a.dtype),))
    low, high = int(a.min()), int(a.max())
    if (0 <= low and high <= 65535) or (-32768 <= low and high <= 32767):
        return OutImage(a, ("uint16", "int16"))
    if all(_exact_in_float32(int(v)) for v in np.unique(a)):
        return OutImage(a.astype(np.float32), ("float32",))
    return None


# ----------------------------------------------------------------------------------------------------- images
DTYPES = (
    "uint8",
    "uint16",
    "int8",
    "int16",
    "int32",
    "uint32",
    "int64",
    "uint64",
    "float16",
    "float32",
    "float64",
    "bool",
)
LABEL_DTYPES = ("uint8", "uint16", "int32", "uint32", "int64")
SHAPES = {
    "1x1": (1, 1),
    "1x7": (1, 7),
    "7x1": (7, 1),
    "2x3": (2, 3),
    "64x64": (64, 64),
    "3d-3x4x5": (3, 4, 5),
    "4d-2x3x4x5": (2, 3, 4, 5),
}


def ramp(shape: tuple[int, ...], dtype: str) -> np.ndarray:
    """An asymmetric pattern (every row, column and axis differs, a transpose changes it) that fits the dtype."""
    n = int(np.prod(shape))
    index = np.arange(n, dtype=np.int64)
    dt = np.dtype(dtype)
    if dt.kind == "b":
        values = (index % 3 == 0) | (index % 7 == 1)
    elif dt.kind in "iu":
        info = np.iinfo(dt)
        span = min(int(info.max) - int(info.min) + 1, 1000003)  # a modulus well inside the range
        values = (index * 37 + 11) % span - (span // 2 if dt.kind == "i" else 0)
    else:
        values = index * 0.375 - 5.25
    return values.astype(dt).reshape(shape)


def extremes(dtype: str) -> np.ndarray:
    """2x3 array of the smallest, largest and neighbouring values of the dtype."""
    dt = np.dtype(dtype)
    if dt.kind == "b":
        return np.array([[True, False, True], [False, False, True]])
    if dt.kind in "iu":
        info = np.iinfo(dt)
        return np.array([[info.min, info.max, 0], [1, info.max - 1, info.min + 1]], dtype=dt)
    info = np.finfo(dt)
    return np.array([[-info.max, info.max, 0.0], [info.tiny, -info.tiny, 1.0]], dtype=dt)


def float_specials(dtype: str) -> np.ndarray:
    """NaN, +-inf, -0.0, a subnormal, the largest finite value."""
    dt = np.dtype(dtype)
    tiny = np.nextafter(dt.type(0), dt.type(1))  # the smallest positive subnormal
    return np.array([[np.nan, np.inf, -np.inf], [-0.0, tiny, np.finfo(dt).max]], dtype=dt)


def _layouts() -> dict[str, np.ndarray]:
    base = ramp((5, 8), "uint16")
    return {
        "fortran-5x4": np.asfortranarray(ramp((5, 4), "uint16")),
        "fortran-3d": np.asfortranarray(ramp((3, 4, 5), "float32")),
        "noncontiguous-step": base[::2, ::-1],  # a view with a negative stride
        "noncontiguous-columns": base[:, 1::3],
        "transposed-view": ramp((3, 5), "uint8").T,
    }


def _image_expect(a: np.ndarray, out_name: str, report: dict[str, Any] | None = None) -> Expect:
    out = expected_image_out(a)
    received = report if report is not None else array_report(a)
    if out is None:
        return Expect(status="FAILED", code="unsupported_dtype", toolerror=True)
    return Expect(received=received, outputs={out_name: out})


def image_cases() -> list[Case]:
    cases: list[Case] = []

    def add(case_id: str, tool: str, a: Any, out_name: str, group: str, heavy: bool = False) -> None:
        paths = ("worker", "cli", "snippet", "notebook") if not heavy else ("worker",)
        cases.append(
            Case(
                "%s/%s" % (tool, case_id),
                tool,
                {out_name: a},
                _image_expect(a, out_name),
                paths,
                heavy,
                group,
            )
        )

    for dtype in DTYPES:
        for name, shape in SHAPES.items():
            add("%s/%s" % (dtype, name), "echo_image", ramp(shape, dtype), "image", "image")
        add("%s/extremes" % dtype, "echo_image", extremes(dtype), "image", "image")
    for dtype in ("float16", "float32", "float64"):
        add("%s/specials" % dtype, "echo_image", float_specials(dtype), "image", "image")
    for name, a in _layouts().items():
        add("layout/%s" % name, "echo_image", a, "image", "image")
    add("float64/beyond-float32", "echo_image", np.array([[1e39, 1.0]], dtype=np.float64), "image", "image")
    add(
        "float64/near-float32-max",
        "echo_image",
        np.array([[3.4e38, -3.4e38]], dtype=np.float64),
        "image",
        "image",
    )
    add("float64/underflow", "echo_image", np.array([[1e-50, 5e-324]], dtype=np.float64), "image", "image")
    add("int32/fits-uint16", "echo_image", np.array([[0, 65535, 7]], dtype=np.int32), "image", "image")
    add(
        "int32/negative-small",
        "echo_image",
        np.array([[-32768, 32767, -1]], dtype=np.int32),
        "image",
        "image",
    )
    add("int32/just-beyond-16-bit", "echo_image", np.array([[65536, 0, 3]], dtype=np.int32), "image", "image")
    add(
        "int32/exact-float32",
        "echo_image",
        np.array([[-(2**31), 2**30, 2**24]], dtype=np.int32),
        "image",
        "image",
    )
    add("int32/inexact-float32", "echo_image", np.array([[2**24 + 1, 0]], dtype=np.int32), "image", "image")
    add("uint64/huge", "echo_image", np.array([[2**63, 1]], dtype=np.uint64), "image", "image")
    add("uint64/beyond-float32", "echo_image", np.array([[2**64 - 1, 1]], dtype=np.uint64), "image", "image")
    # the same arrays, input direction only (the echo cannot write the ones that must fail)
    for dtype in DTYPES:
        a = extremes(dtype)
        cases.append(
            Case(
                "echo_optional_image/%s/extremes" % dtype,
                "echo_optional_image",
                {"image": a},
                Expect(received={"is_none": False, **array_report(a)}),
                ("worker", "cli", "snippet", "notebook"),
                False,
                "image",
            )
        )
    # shared memory hands over the array without a file: every dtype, 2D and 3D, plus the refusals
    for dtype in DTYPES:
        for name in ("2x3", "3d-3x4x5"):
            a = ramp(SHAPES[name], dtype)
            cases.append(
                Case(
                    "echo_image/shm/%s/%s" % (dtype, name),
                    "echo_image",
                    {"image": Shm(a)},
                    _image_expect(a, "image"),
                    ("worker",),
                    False,
                    "image",
                )
            )
    cases.append(
        Case(
            "echo_image/shm/empty",
            "echo_image",
            {"image": Shm(np.zeros((0, 3), np.uint8))},
            Expect(status="FAILED", code="empty_image", toolerror=True),
            ("worker",),
            False,
            "image",
        )
    )
    # a missing file, a directory, a text file and a truncated TIFF are refused with a message, never a traceback
    cases.append(
        Case(
            "echo_image/missing-file",
            "echo_image",
            {"image": MissingPath("nothing.tif")},
            Expect(status="FAILED", code="file_not_found", toolerror=True, message="nothing.tif"),
            ("worker", "cli"),
            False,
            "image",
        )
    )
    cases.append(
        Case(
            "echo_image/not-an-image",
            "echo_image",
            {"image": FileSpec("not_an_image.tif", b"this is not a tiff file")},
            Expect(status="FAILED", code="unreadable_image", toolerror=True),
            ("worker", "cli"),
            False,
            "image",
        )
    )
    cases.append(
        Case(
            "echo_image/empty-file",
            "echo_image",
            {"image": FileSpec("zero_bytes.tif", b"")},
            Expect(status="FAILED", code="unreadable_image", toolerror=True),
            ("worker",),
            False,
            "image",
        )
    )
    # large images only in the nightly profile
    if nightly():
        add("float32/2048x2048", "echo_image", ramp((2048, 2048), "float32"), "image", "image", heavy=True)
        add("uint16/4096x3000", "echo_image", ramp((4096, 3000), "uint16"), "image", "image", heavy=True)
        add("uint8/3d-64x512x512", "echo_image", ramp((64, 512, 512), "uint8"), "image", "image", heavy=True)
    return cases


def labels_cases() -> list[Case]:
    cases: list[Case] = []
    for dtype in LABEL_DTYPES:
        for name in ("1x1", "1x7", "7x1", "2x3", "64x64", "3d-3x4x5"):
            a = ramp(SHAPES[name], dtype) % 11  # labels: small non-negative-ish integers
            cases.append(
                Case(
                    "echo_labels/%s/%s" % (dtype, name),
                    "echo_labels",
                    {"labels": a},
                    _image_expect(a, "labels"),
                    ("worker", "cli", "snippet", "notebook") if a.size <= 4096 else ("worker",),
                    False,
                    "labels",
                )
            )
        a = extremes(dtype)
        cases.append(
            Case(
                "echo_labels/%s/extremes" % dtype,
                "echo_labels",
                {"labels": a},
                _image_expect(a, "labels"),
                ("worker",),
                False,
                "labels",
            )
        )
    a = np.zeros((6, 7), np.uint16)
    a[1:3, 1:4] = 1
    a[4:6, 5:7] = 65535
    cases.append(
        Case(
            "echo_labels/uint16/with-max-label",
            "echo_labels",
            {"labels": a},
            _image_expect(a, "labels"),
            ("worker",),
            False,
            "labels",
        )
    )
    return cases


# ------------------------------------------------------------------------------------------------------ scalars
INT_OK = [
    0,
    1,
    -1,
    2,
    255,
    256,
    65535,
    65536,
    2**31 - 1,
    2**31,
    -(2**31),
    2**53 - 1,
    2**53,
    2**53 + 1,
    2**63 - 1,
    2**63,
    -(2**63),
    2**64,
    10**30,
    -(10**30),
]
FLOAT_OK = [
    0.0, -0.0, 1.0, -1.0, 0.1, 0.1 + 0.2, 1 / 3, 2 / 3, 1e-7, 123456789.123456789, 1e15, 2.0**53, 2.0**53 + 2,
    1e-308, 2.2250738585072014e-308, 5e-324, -5e-324, 1.7976931348623157e308, -1.7976931348623157e308,
    math.pi, math.e,
]  # fmt: skip
FLOAT_OK = list(
    {v.hex(): v for v in FLOAT_OK}.values()
)  # 0.1 + 0.2 and 5e-324 are spelled twice above (0.0 and -0.0 differ)
STRINGS: dict[str, str] = {
    "empty": "",
    "space": " ",
    "leading-trailing-spaces": "  padded text  ",
    "tab": "a\tb\t",
    "newline": "line1\nline2\n",
    "crlf": "x\r\ny\r\n",
    "cr-only": "a\rb",
    "single-quote": "it's",
    "double-quote": 'say "hi"',
    "both-quotes": """it's "both" `tick`""",
    "backslash": "a\\b\\\\c\\",
    "windows-path": "C:\\Program Files\\Lab Tools\\x y\\z.tif",
    "trailing-backslash": "C:\\dir\\",
    "emoji": "emoji \U0001f600\U0001f389\U0001f9ec",
    "rtl": "\u05e2\u05d1\u05e8\u05d9\u05ea \u0645\u0631\u062d\u0628\u0627 abc",
    "combining": "e\u0301 vs \u00e9",
    "zero-width": "a\u200bb\u200dc\ufeffd",
    "nbsp-and-line-separators": "a\u00a0b\u2028c\u2029d",
    "control-chars": "bell\x07 esc\x1b[31mred\x1b[0m del\x7f",
    "cjk": "\u65e5\u672c\u8a9e \u4e2d\u6587 \ud55c\uad6d\uc5b4",
    "micro-and-arrow": "\u00b5m \u2192 \u2713 na\u00efve",
    "shell-command-substitution": "$(touch /tmp/pwned) `id` ${HOME}",
    "shell-operators": "a; b && c | d > e < f & g",
    "shell-globs": "* ? [a-z] {a,b} ~ ~/x",
    "shell-variables": "$HOME %PATH% !! ^caret %%",
    "option-like": "--help",
    "dash": "-x",
    "equals-only": "=",
    "equals-inside": "a=b=c",
    "path-parent": "../../etc/passwd",
    "path-absolute": "/etc/passwd",
    "path-dot": ".",
    "path-dotdot": "..",
    "path-url": "file:///etc/passwd",
    "path-unc": "\\\\server\\share\\x",
    "json-looking": '{"a": [1, 2, null], "b": "c"}',
    "null-text": "null",
    "true-text": "true",
    "number-text": "007",
    "long-ascii-15k": "x" * 15_000,
    "long-unicode-4k": "\u00e9\U0001f600" * 1_000,
    "long-200k": "x" * 200_000,
    "long-unicode-50k": "\u00e9\U0001f600" * 25_000,
}
COMMAND_LINE_BYTES = (
    20_000  # a command line holds about 32 000 characters on Windows, 128 000 bytes per argument on Linux
)
STRINGS_WORKER_ONLY: dict[str, str] = {  # cannot be written on a command line (NUL, lone surrogate)
    "nul": "a\x00b",
    "lone-surrogate": "a\ud800b",
}
STRINGS_HEAVY = {"long-5m": "ab" * 2_500_000}


def _scalar_cases() -> list[Case]:
    cases: list[Case] = []
    all_paths = ("worker", "cli", "snippet", "notebook")

    def ok(
        case_id: str,
        tool: str,
        value: Any,
        expected: Any,
        group: str,
        paths: tuple[str, ...] = ("worker", "cli", "snippet"),
    ) -> None:
        cases.append(
            Case(
                "%s/%s" % (tool, case_id),
                tool,
                {"value": value},
                Expect(received=scalar_report(expected)),
                paths,
                False,
                group,
            )
        )

    def bad(
        case_id: str,
        tool: str,
        value: Any,
        code: str,
        group: str,
        toolerror: bool = True,
        paths: tuple[str, ...] = ("worker",),
    ) -> None:
        cases.append(
            Case(
                "%s/%s" % (tool, case_id),
                tool,
                {"value": value},
                Expect(status="FAILED", code=code, toolerror=toolerror),
                paths,
                False,
                group,
            )
        )

    for v in INT_OK:
        ok(
            "ok/%d" % v,
            "echo_int",
            v,
            v,
            "int",
            all_paths if abs(v) <= 2**31 else ("worker", "cli", "snippet"),
        )
    for v in (3.0, -2.0, 1000.0, 0.0, -0.0):
        ok("integral-float/%r" % v, "echo_int", v, int(v), "int", ("worker", "snippet"))
    for label, v in (
        ("fraction", 3.5),
        ("tiny-fraction", 0.1),
        ("bool-true", True),
        ("bool-false", False),
        ("digit-text", "3"),
    ):
        bad(label, "echo_int", v, "invalid_parameter", "int")
    cases.append(
        Case(
            "echo_int/missing",
            "echo_int",
            {},
            Expect(status="FAILED", code="missing_parameter", toolerror=True),
            ("worker",),
            False,
            "int",
        )
    )
    cases.append(
        Case(
            "echo_int/null",
            "echo_int",
            {"value": None},
            Expect(status="FAILED", code="missing_parameter", toolerror=True),
            ("worker",),
            False,
            "int",
        )
    )
    for label, v in (
        ("word", "abc"),
        ("empty-text", ""),
        ("decimal-text", "3.0"),
        ("list", [1]),
        ("dict", {}),
        ("nan", float("nan")),
        ("inf", float("inf")),
        ("minus-inf", float("-inf")),
    ):
        bad(label, "echo_int", v, "invalid_parameter", "int", toolerror=True)

    for v in FLOAT_OK:
        ok(
            "ok/%s" % v.hex(),
            "echo_float",
            v,
            v,
            "float",
            all_paths if (abs(v) < 1e9 or v == 1e15) else ("worker", "cli", "snippet"),
        )
    for v in (3, -7, 0, 10**20, 2**53 + 1, 10**300):
        ok(
            "int-sent/%d" % (v if abs(v) < 10**6 else len(str(v))),
            "echo_float",
            v,
            float(v),
            "float",
            ("worker", "snippet"),
        )
    for label, v in (
        ("bool-true", True),
        ("bool-false", False),
        ("nan", float("nan")),
        ("inf", float("inf")),
        ("minus-inf", float("-inf")),
    ):
        bad(label, "echo_float", v, "invalid_parameter", "float")
    for label, v in (
        ("word", "abc"),
        ("empty-text", ""),
        ("list", [1.5]),
        ("dict", {}),
        ("huge-int", 10**400),
    ):
        bad(label, "echo_float", v, "invalid_parameter", "float", toolerror=True)
    cases.append(
        Case(
            "echo_float/missing",
            "echo_float",
            {},
            Expect(status="FAILED", code="missing_parameter", toolerror=True),
            ("worker",),
            False,
            "float",
        )
    )

    for label, text in {**STRINGS, **STRINGS_WORKER_ONLY}.items():
        cli_ok = label not in STRINGS_WORKER_ONLY
        paths = (
            ("worker",)
            + (("cli", "snippet") if cli_ok and len(text.encode("utf-8")) < COMMAND_LINE_BYTES else ())
            + (("notebook",) if cli_ok and len(text) < 1000 else ())
        )
        ok("text/%s" % label, "echo_string", text, text, "string", paths)
    for label, text in STRINGS_HEAVY.items():
        cases.append(
            Case(
                "echo_string/text/%s" % label,
                "echo_string",
                {"value": text},
                Expect(received=scalar_report(text)),
                ("worker",),
                True,
                "string",
            )
        )
    cases.append(
        Case(
            "echo_string/missing",
            "echo_string",
            {},
            Expect(status="FAILED", code="missing_parameter", toolerror=True),
            ("worker",),
            False,
            "string",
        )
    )

    for v in (True, False):
        ok("ok/%s" % v, "echo_bool", v, v, "bool", all_paths)
    for label, v in (
        ("one", 1),
        ("zero", 0),
        ("text-true", "true"),
        ("text-True", "True"),
        ("text-false", "false"),
        ("text-yes", "yes"),
        ("float-one", 1.0),
        ("empty-text", ""),
        ("list", []),
        ("dict", {}),
    ):
        bad(label, "echo_bool", v, "invalid_parameter", "bool")
    cases.append(
        Case(
            "echo_bool/missing",
            "echo_bool",
            {},
            Expect(status="FAILED", code="missing_parameter", toolerror=True),
            ("worker",),
            False,
            "bool",
        )
    )
    return cases


def _choice_cases() -> list[Case]:
    cases: list[Case] = []
    texts = ["alpha", "beta", "gamma", "with space", "\u00fcn\u00ef", ""]
    for v in texts:
        cases.append(
            Case(
                "echo_choice/ok/%s" % (v or "empty"),
                "echo_choice",
                {"value": v},
                Expect(received=scalar_report(v)),
                ("worker", "cli", "snippet", "notebook"),
                False,
                "choice",
            )
        )
    for label, v in (
        ("case", "Alpha"),
        ("unknown", "delta"),
        ("leading-space", " alpha"),
        ("trailing-space", "alpha "),
        ("int", 1),
        ("bool", True),
        ("list", ["alpha"]),
        ("float", 1.5),
    ):
        cases.append(
            Case(
                "echo_choice/invalid/%s" % label,
                "echo_choice",
                {"value": v},
                Expect(status="FAILED", code="invalid_parameter", toolerror=True),
                ("worker",),
                False,
                "choice",
            )
        )
    for v in (1, 2, 3):
        cases.append(
            Case(
                "echo_number_choice/ok/%d" % v,
                "echo_number_choice",
                {"value": v},
                Expect(received=scalar_report(v)),
                ("worker", "cli", "snippet", "notebook"),
                False,
                "choice",
            )
        )
    for label, v in (
        ("zero", 0),
        ("four", 4),
        ("true", True),
        ("float-one", 1.0),
        ("text-one", "1"),
        ("false", False),
    ):
        cases.append(
            Case(
                "echo_number_choice/invalid/%s" % label,
                "echo_number_choice",
                {"value": v},
                Expect(status="FAILED", code="invalid_parameter", toolerror=True),
                ("worker",),
                False,
                "choice",
            )
        )
    for member in ("red", "green", "blue"):
        report = {**scalar_report(member), "is_member": True, "member": member.upper()}
        cases.append(
            Case(
                "echo_enum/ok/%s" % member,
                "echo_enum",
                {"value": member},
                Expect(received=report),
                ("worker", "cli", "snippet", "notebook"),
                False,
                "choice",
            )
        )
    for label, v in (("member-name", "RED"), ("unknown", "purple"), ("int", 1)):
        cases.append(
            Case(
                "echo_enum/invalid/%s" % label,
                "echo_enum",
                {"value": v},
                Expect(status="FAILED", code="invalid_parameter", toolerror=True),
                ("worker",),
                False,
                "choice",
            )
        )
    cases.append(
        Case(
            "echo_enum/default",
            "echo_enum",
            {},
            Expect(received={**scalar_report("green"), "is_member": True, "member": "GREEN"}),
            ("worker", "cli", "snippet"),
            False,
            "choice",
        )
    )
    # radio widget: the same rules as any other choice
    for v in ("one", "two", "three"):
        cases.append(
            Case(
                "echo_radio/ok/%s" % v,
                "echo_radio",
                {"value": v},
                Expect(received=scalar_report(v)),
                ("worker", "cli", "snippet", "notebook"),
                False,
                "widget",
            )
        )
    cases.append(
        Case(
            "echo_radio/default",
            "echo_radio",
            {},
            Expect(received=scalar_report("two")),
            ("worker", "cli", "snippet"),
            False,
            "widget",
        )
    )
    cases.append(
        Case(
            "echo_radio/invalid",
            "echo_radio",
            {"value": "four"},
            Expect(status="FAILED", code="invalid_parameter", toolerror=True),
            ("worker",),
            False,
            "widget",
        )
    )
    for member in ("red", "green", "blue"):
        report = {**scalar_report(member), "is_member": True}
        cases.append(
            Case(
                "echo_radio_enum/ok/%s" % member,
                "echo_radio_enum",
                {"value": member},
                Expect(received=report),
                ("worker", "cli", "snippet"),
                False,
                "widget",
            )
        )
    return cases


def _default_cases() -> list[Case]:
    defaults = {
        "number": scalar_report(7),
        "ratio": scalar_report(0.25),
        "text": scalar_report("dflt"),
        "flag": scalar_report(True),
        "mode": scalar_report("b"),
    }
    cases = [
        Case(
            "echo_defaults/empty-request",
            "echo_defaults",
            {},
            Expect(received=defaults),
            ("worker", "cli", "snippet", "notebook"),
            False,
            "default",
        )
    ]
    for mode in ("a", "b"):
        cases.append(
            Case(
                "echo_defaults/explicit-mode-%s" % mode,
                "echo_defaults",
                {"mode": mode},
                Expect(received={**defaults, "mode": scalar_report(mode)}),
                ("worker",),
                False,
                "default",
            )
        )
    cases.append(
        Case(
            "echo_defaults/all-null",
            "echo_defaults",
            {k: None for k in defaults},
            Expect(received=defaults),
            ("worker",),
            False,
            "default",
        )
    )
    for name, value, kind_value in (
        ("number", 0, 0),
        ("ratio", 0.0, 0.0),
        ("text", "", ""),
        ("flag", False, False),
        ("mode", "a", "a"),
    ):
        # a falsy value is a value: it must not fall back to the default
        expected = {**defaults, name: scalar_report(kind_value)}
        cases.append(
            Case(
                "echo_defaults/falsy-%s" % name,
                "echo_defaults",
                {name: value},
                Expect(received=expected),
                ("worker", "cli", "snippet", "notebook"),
                False,
                "default",
            )
        )
    return cases


def _nullable_cases() -> list[Case]:
    cases: list[Case] = []
    unset = {"value": None, "type": "NoneType", "repr": "None", "is_none": True}
    samples = {
        "echo_optional_int": [0, 1, -3, 2**40],
        "echo_optional_float": [0.0, -0.0, 0.5, 1e-300],
        "echo_optional_string": ["", " ", "text", "None", "null"],
        "echo_optional_bool": [False, True],
        "echo_optional_choice": ["x", "y"],
    }
    for tool, values in samples.items():
        cases.append(
            Case(
                "%s/omitted" % tool,
                tool,
                {},
                Expect(received=unset),
                ("worker", "cli", "snippet", "notebook"),
                False,
                "nullable",
            )
        )
        cases.append(
            Case(
                "%s/null" % tool,
                tool,
                {"value": None},
                Expect(received=unset),
                ("worker", "snippet"),
                False,
                "nullable",
            )
        )
        for v in values:
            expected = {**scalar_report(v), "is_none": False}
            cases.append(
                Case(
                    "%s/set/%r" % (tool, v),
                    tool,
                    {"value": v},
                    Expect(received=expected),
                    ("worker", "cli", "snippet", "notebook"),
                    False,
                    "nullable",
                )
            )
    cases.append(
        Case(
            "echo_optional_choice/invalid",
            "echo_optional_choice",
            {"value": "z"},
            Expect(status="FAILED", code="invalid_parameter", toolerror=True),
            ("worker",),
            False,
            "nullable",
        )
    )
    cases.append(
        Case(
            "echo_optional_int/invalid",
            "echo_optional_int",
            {"value": 1.5},
            Expect(status="FAILED", code="invalid_parameter", toolerror=True),
            ("worker",),
            False,
            "nullable",
        )
    )
    cases.append(
        Case(
            "echo_optional_image/omitted",
            "echo_optional_image",
            {},
            Expect(received={"is_none": True}),
            ("worker", "cli", "snippet", "notebook"),
            False,
            "nullable",
        )
    )
    return cases


def _bound_cases() -> list[Case]:
    cases: list[Case] = []

    def bounded(
        tool: str, low: Any, high: Any, kind: str, extra_ok: list[Any], group: str = "bounds"
    ) -> None:
        make = (lambda v: v) if kind == "int" else float
        inside = [make(v) for v in (low, high) if v is not None] + [make(v) for v in extra_ok]
        for v in inside:
            cases.append(
                Case(
                    "%s/ok/%r" % (tool, v),
                    tool,
                    {"value": v},
                    Expect(received=scalar_report(make(v))),
                    ("worker", "cli", "snippet"),
                    False,
                    group,
                )
            )
        outside: list[Any] = []
        if low is not None:
            outside += [low - 1] if kind == "int" else [float(np.nextafter(float(low), -math.inf)), low - 1.0]
        if high is not None:
            outside += (
                [high + 1] if kind == "int" else [float(np.nextafter(float(high), math.inf)), high + 1.0]
            )
        for v in outside:
            bound = "minimum" if (low is not None and v < low) else "maximum"
            cases.append(
                Case(
                    "%s/outside/%r" % (tool, v), tool, {"value": v},
                    Expect(status="FAILED", code="invalid_parameter", toolerror=True, message=("must be >= " if bound == "minimum" else "must be <= ")),
                    ("worker", "cli"), False, group,
                )  # fmt: skip
            )

    bounded("echo_bounded_int", -5, 10, "int", [0, 3])
    bounded("echo_bounded_float", -0.5, 1.5, "float", [0.0, -0.0, 1.0, 0.5])
    bounded("echo_slider_int", 0, 255, "int", [1, 128, 254], "widget")
    bounded("echo_slider_float", 0.0, 1.0, "float", [0.5, 1e-9, 0.9999999999999999], "widget")
    bounded("echo_min_only", 0.0, None, "float", [1e300, 5.0])
    bounded("echo_max_only", None, 100, "int", [-(10**20), 99])
    # the default of a slider reaches the tool when nothing is sent
    cases.append(
        Case(
            "echo_slider_int/default",
            "echo_slider_int",
            {},
            Expect(received=scalar_report(128)),
            ("worker", "cli", "snippet"),
            False,
            "widget",
        )
    )
    cases.append(
        Case(
            "echo_slider_float/default",
            "echo_slider_float",
            {},
            Expect(received=scalar_report(0.5)),
            ("worker", "cli", "snippet"),
            False,
            "widget",
        )
    )
    return cases


# -------------------------------------------------------------------------------------------------------- tables
UNICODE_COLUMNS = [
    "\u00b5m",
    "\u5217",
    "emoji \U0001f600",
    "a b",
    'q"uote',
    "com,ma",
    "new\nline",
    " lead",
    "x",
]


def _kinds(frame: pd.DataFrame) -> list[str]:
    """Kind letters of the columns the way a reader of the CSV sees them (text columns are 'O')."""
    out = []
    for name in frame.columns:
        dtype = frame[name].dtype
        out.append(
            "b" if dtype.kind == "b" else "i" if dtype.kind in "iu" else "f" if dtype.kind == "f" else "O"
        )
    return out


def _cells(frame: pd.DataFrame) -> dict[str, list[Any]]:
    data: dict[str, list[Any]] = {}
    for i, name in enumerate(frame.columns):
        column = frame.iloc[:, i]
        data[str(i)] = [
            None if (isinstance(v, float) and math.isnan(v)) else (v.item() if hasattr(v, "item") else v)
            for v in column.tolist()
        ]
    return data


def table_frames() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(RNG_SEED)
    return {
        "ints": pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}),
        "mixed-dtypes": pd.DataFrame(
            {"i": [1, -2, 3], "f": [0.5, 1.5, -2.25], "s": ["x", "y z", "q,r"], "b": [True, False, True]}
        ),
        "unicode-and-awkward-names": pd.DataFrame(
            {name: [i, i + 1] for i, name in enumerate(UNICODE_COLUMNS)}
        ),
        "nan-cells": pd.DataFrame(
            {"x": [1.0, np.nan, 3.0], "y": [np.nan, np.nan, np.nan], "z": [0.5, 0.25, np.nan]}
        ),
        "one-row": pd.DataFrame({"a": [1], "b": ["only"]}),
        "header-only": pd.DataFrame({"a": pd.Series([], dtype="int64"), "b": pd.Series([], dtype="float64")}),
        "single-column": pd.DataFrame({"only": [3, 1, 2]}),
        "awkward-cells": pd.DataFrame(
            {
                "t": [
                    "comma, inside",
                    'quote " inside',
                    "line\nbreak",
                    "caf\u00e9 \U0001f600",
                    "  spaced  ",
                    "tab\there",
                    "'single'",
                ]
            }
        ),
        "text-that-pandas-calls-missing": pd.DataFrame(
            {"t": ["NA", "null", "None", "N/A", "nan", "NaN", "n/a", "x"]}
        ),
        "float-extremes": pd.DataFrame(
            {
                "f": [
                    0.0,
                    -0.0,
                    1e-308,
                    1.7976931348623157e308,
                    -1.7976931348623157e308,
                    np.inf,
                    -np.inf,
                    5e-324,
                ]
            }
        ),
        "int-extremes": pd.DataFrame({"i": [0, -1, 2**31, -(2**31), 2**53, 2**62, -(2**63) + 1, 2**63 - 1]}),
        "float-digits": pd.DataFrame(
            {
                "f": [
                    0.1,
                    0.1 + 0.2,
                    1 / 3,
                    2 / 3,
                    123456789.123456789,
                    1.1,
                    2.675,
                    8.41,
                    9007199254740993.0,
                    1e22,
                    1e23,
                    5e-324,
                    2.2250738585072011e-308,
                ]
            }
        ),
        "random-floats": pd.DataFrame({"f": rng.normal(size=300) * 10.0 ** rng.integers(-12, 12, size=300)}),
        "wide-200": pd.DataFrame({"c%d" % i: [i, i + 1] for i in range(200)}),
        "rows-10k": pd.DataFrame(
            {
                "i": np.arange(10_000),
                "f": np.arange(10_000) * 0.25,
                "s": ["row %d" % i for i in range(10_000)],
            }
        ),
    }


def table_report(frame: pd.DataFrame) -> dict[str, Any]:
    """What `echo_table` must report about the table it read: names, size, kinds, a digest of every cell and, for small
    tables, the cells (NaN and infinity are not JSON numbers: they are reported as null)."""
    columns = [str(c) for c in frame.columns]
    report: dict[str, Any] = {"columns": columns, "n_rows": int(len(frame))}
    if len(frame):
        report["kinds"] = _kinds(frame)
    cells = [list(_cells(frame)[str(i)]) for i in range(len(columns))]  # NaN as None, infinity kept
    report["cells_digest"] = hashlib.sha256(
        json.dumps(cells, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if frame.size <= 2000:
        report["cells"] = [
            [None if (isinstance(v, float) and math.isinf(v)) else v for v in column] for column in cells
        ]
    return report


def _table_expect(frame: pd.DataFrame, out_name: str) -> Expect:
    columns = [str(c) for c in frame.columns]
    return Expect(received=table_report(frame), outputs={out_name: OutTable(columns, _cells(frame))})


def table_cases() -> list[Case]:
    cases: list[Case] = []
    for name, frame in table_frames().items():
        heavy = False
        paths = ("worker", "cli", "snippet", "notebook") if len(frame) <= 1000 else ("worker",)
        cases.append(
            Case(
                "echo_table/%s" % name,
                "echo_table",
                {"table": frame},
                _table_expect(frame, "table"),
                paths,
                heavy,
                "table",
            )
        )
    if nightly():
        big = pd.DataFrame(
            {"i": np.arange(300_000), "f": np.arange(300_000) * 0.5, "s": ["r%d" % i for i in range(300_000)]}
        )
        cases.append(
            Case(
                "echo_table/rows-300k",
                "echo_table",
                {"table": big},
                _table_expect(big, "table"),
                ("worker",),
                True,
                "table",
            )
        )
    # names a CSV header cannot carry unchanged through pandas (duplicates, empty): the host must still read what it wrote
    dup = pd.DataFrame([[1, 2], [3, 4]], columns=["a", "a"])
    for name in (
        "ints",
        "mixed-dtypes",
        "nan-cells",
        "float-digits",
        "random-floats",
        "awkward-cells",
        "int-extremes",
        "float-extremes",
        "unicode-and-awkward-names",
        "rows-10k",
    ):
        frame = table_frames()[name]
        text = json.dumps({str(c): frame[c].tolist() for c in frame.columns})
        for form in ("dataframe", "dict", "records"):
            if form == "records" and name == "rows-10k":
                continue
            cases.append(
                Case(
                    "table_from_json/%s/%s" % (name, form),
                    "table_from_json",
                    {"columns_json": text, "form": form},
                    Expect(outputs={"table": OutTable([str(c) for c in frame.columns], _cells(frame))}),
                    ("worker", "cli") if len(text) < COMMAND_LINE_BYTES else ("worker",),
                    False,
                    "table",
                )
            )
    cases.append(
        Case(
            "table_from_json/no-rows",
            "table_from_json",
            {"columns_json": '{"a": [], "b": []}'},
            Expect(outputs={"table": OutTable(["a", "b"], {"0": [], "1": []})}),
            ("worker",),
            False,
            "table",
        )
    )
    cases.append(
        Case(
            "table_from_json/missing-cells-are-empty",
            "table_from_json",
            {"columns_json": '{"a": [1, null, 3], "b": ["x", null, "z"]}'},
            Expect(outputs={"table": OutTable(["a", "b"], {"0": [1.0, None, 3.0], "1": ["x", None, "z"]})}),
            ("worker",),
            False,
            "table",
        )
    )
    cases.append(
        Case(
            "echo_table/duplicate-column-names",
            "echo_table",
            {"table": dup},
            Expect(
                received={"columns": ["a", "a"], "n_rows": 2},
                outputs={"table": OutTable(["a", "a"], {"0": [1, 3], "1": [2, 4]})},
            ),
            ("worker",),
            False,
            "table",
        )
    )
    empty_name = pd.DataFrame([[1, 2], [3, 4]], columns=["", "b"])
    cases.append(
        Case(
            "echo_table/empty-column-name",
            "echo_table",
            {"table": empty_name},
            Expect(
                received={"columns": ["", "b"], "n_rows": 2},
                outputs={"table": OutTable(["", "b"], {"0": [1, 3], "1": [2, 4]})},
            ),
            ("worker",),
            False,
            "table",
        )
    )
    cases.append(
        Case(
            "echo_table/no-header-no-rows",
            "echo_table",
            {"table": FileSpec("empty.csv", b"")},
            Expect(status="FAILED", toolerror=True),
            ("worker", "cli"),
            False,
            "table",
        )
    )
    cases.append(
        Case(
            "echo_table/missing-file",
            "echo_table",
            {"table": MissingPath("nothing.csv")},
            Expect(status="FAILED", code="file_not_found", toolerror=True, message="nothing.csv"),
            ("worker", "cli"),
            False,
            "table",
        )
    )
    cases.append(
        Case(
            "echo_table/binary-garbage",
            "echo_table",
            {"table": FileSpec("garbage.csv", bytes(range(256)) * 4)},
            Expect(status="FAILED", toolerror=True),
            ("worker",),
            False,
            "table",
        )
    )
    return cases


# --------------------------------------------------------------------------------------------------------- points
def _points_expect(frame: pd.DataFrame) -> Expect:
    """What a host reads from a points result: y and x first (as floats), then the other columns in their order."""
    others = [c for c in frame.columns if c not in ("y", "x")]
    columns = ["y", "x", *others]
    data = {str(i): _float_or_cell(frame[c].tolist(), c in ("y", "x")) for i, c in enumerate(columns)}
    return Expect(outputs={"points": OutPoints(columns, data)})


def _float_or_cell(values: list[Any], as_float: bool) -> list[Any]:
    out = []
    for v in values:
        if as_float:
            out.append(float(v))
        else:
            out.append(
                None if (isinstance(v, float) and math.isnan(v)) else (v.item() if hasattr(v, "item") else v)
            )
    return out


def points_cases() -> list[Case]:
    cases: list[Case] = []
    frames = {
        "integer-centres": pd.DataFrame({"y": [0, 3, 10], "x": [0, 4, 99]}),
        "asymmetric-yx": pd.DataFrame({"y": [1.0, 2.0, 3.0, 4.0], "x": [10.0, 20.0, 30.0, 40.0]}),
        "x-before-y": pd.DataFrame({"x": [5.0, 6.0], "y": [7.0, 8.0]}),
        "with-properties": pd.DataFrame(
            {
                "y": [1.5, 2.5],
                "x": [3.5, 4.5],
                "label": [1, 2],
                "score": [0.25, np.nan],
                "name": ["a b", "\u00e9\U0001f600"],
            }
        ),
        "one-point": pd.DataFrame({"y": [2.5], "x": [-1.5]}),
        "zero-points": pd.DataFrame(
            {"y": pd.Series([], dtype="float64"), "x": pd.Series([], dtype="float64")}
        ),
        "negative-and-zero": pd.DataFrame({"y": [-0.0, -5.5, 0.0], "x": [-1e-9, 0.0, -0.0]}),
        "huge-coordinates": pd.DataFrame(
            {"y": [1e15, -1e15, 1e300], "x": [1.7976931348623157e308, 2.0**53, 5e-324]}
        ),
        "many-1000": pd.DataFrame({"y": np.arange(1000) * 0.5, "x": np.arange(1000)[::-1] * 1.25}),
    }
    for name, frame in frames.items():
        cases.append(
            Case(
                "echo_points/%s" % name,
                "echo_points",
                {"points": frame},
                _points_expect(frame),
                ("worker", "cli"),
                False,
                "points",
            )
        )
    if nightly():
        big = pd.DataFrame({"y": np.arange(100_000) * 0.5, "x": np.arange(100_000) * 0.25})
        cases.append(
            Case(
                "echo_points/many-100k",
                "echo_points",
                {"points": big},
                _points_expect(big),
                ("worker",),
                True,
                "points",
            )
        )
    bad = {
        "missing-x": (pd.DataFrame({"y": [1.0]}), "bad_return"),
        "missing-both": (pd.DataFrame({"a": [1.0]}), "bad_return"),
        "nan-y": (pd.DataFrame({"y": [1.0, np.nan], "x": [1.0, 2.0]}), "bad_return"),
        "inf-x": (pd.DataFrame({"y": [1.0, 2.0], "x": [1.0, np.inf]}), "bad_return"),
        "minus-inf-x": (pd.DataFrame({"y": [1.0, 2.0], "x": [-np.inf, 1.0]}), "bad_return"),
    }
    for name, (frame, code) in bad.items():
        cases.append(
            Case(
                "echo_points/invalid/%s" % name,
                "echo_points",
                {"points": frame},
                Expect(status="FAILED", code=code, toolerror=True),
                ("worker",),
                False,
                "points",
            )
        )
    for label, (rows, columns, spacing) in {
        "2x3": (2, 3, 1.5),
        "1x1": (1, 1, 1.0),
        "zero-rows": (0, 3, 1.0),
        "zero-columns": (3, 0, 1.0),
        "spacing-zero": (2, 2, 0.0),
        "huge-spacing": (2, 2, 1e15),
        "spacing-0.1": (1, 7, 0.1),
        "30x30": (30, 30, 0.5),
        "1x1000": (1, 1000, 2.0),
    }.items():
        ys = [r * spacing for r in range(rows) for c in range(columns)]
        xs = [c * spacing for r in range(rows) for c in range(columns)]
        frame = pd.DataFrame({"y": ys, "x": xs, "label": list(range(1, len(ys) + 1))})
        if not len(ys):
            frame = pd.DataFrame(
                {
                    "y": pd.Series([], dtype="float64"),
                    "x": pd.Series([], dtype="float64"),
                    "label": pd.Series([], dtype="int64"),
                }
            )
        cases.append(
            Case(
                "grid_points/%s" % label,
                "grid_points",
                {"rows": rows, "columns": columns, "spacing": spacing},
                _points_expect(frame),
                ("worker", "cli", "snippet"),
                False,
                "points",
            )
        )
    return cases


# --------------------------------------------------------------------------------------------------------- shapes
def _square(y0: float, x0: float, size: float) -> list[list[float]]:
    """[y, x] vertices of an axis-aligned square (not closed)."""
    return [[y0, x0], [y0, x0 + size], [y0 + size, x0 + size], [y0 + size, x0]]


def _geo_ring(yx: list[list[float]], closed: bool = False) -> list[list[float]]:
    ring = [[x, y] for y, x in yx]
    return ring if closed else ring + [ring[0]]


def _feature(rings: list[list[list[float]]], **props: Any) -> dict[str, Any]:
    return {"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": rings}}


def shapes_cases() -> list[Case]:
    cases: list[Case] = []
    outer = _geo_ring(_square(0.0, 0.0, 10.0))
    hole = _geo_ring(_square(3.0, 3.0, 4.0))
    collections = {
        "empty-collection": {"type": "FeatureCollection", "features": []},
        "one-polygon": {"type": "FeatureCollection", "features": [_feature([outer], label=1, area=100)]},
        "polygon-with-hole": {"type": "FeatureCollection", "features": [_feature([outer, hole], label=2)]},
        "multipolygon": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"label": 3},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [[outer], [_geo_ring(_square(20.0, 20.0, 5.0))]],
                    },
                }
            ],
        },
        "multipolygon-with-hole": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [[outer, hole], [_geo_ring(_square(20.0, 20.0, 5.0))]],
                    },
                }
            ],
        },
        "integer-centres": {
            "type": "FeatureCollection",
            "features": [_feature([[[0, 0], [4, 0], [4, 7], [0, 7], [0, 0]]], label=5)],
        },
        "huge-coordinates": {
            "type": "FeatureCollection",
            "features": [
                _feature([_geo_ring(_square(1e15, -1e15, 1e14))]),
                _feature([_geo_ring(_square(1e300, 5e-324, 1e299))]),
            ],
        },
        "unicode-properties": {
            "type": "FeatureCollection",
            "features": [
                _feature(
                    [outer],
                    name="\u00e9\U0001f600 \u00b5m",
                    note="line\nbreak",
                    flag=True,
                    none=None,
                    nested={"a": [1, 2]},
                )
            ],
        },
        "many-200": {
            "type": "FeatureCollection",
            "features": [
                _feature([_geo_ring(_square(float(i), float(2 * i), 0.5))], label=i) for i in range(200)
            ],
        },
        "negative-coordinates": {
            "type": "FeatureCollection",
            "features": [_feature([_geo_ring(_square(-10.5, -3.25, 2.0))])],
        },
    }
    for name, collection in collections.items():
        expected = Expect(outputs={"shapes": OutShapes(collection)})
        cases.append(
            Case(
                "echo_geojson/%s" % name,
                "echo_geojson",
                {"geojson": JsonFile("shapes.geojson", collection)},
                expected,
                ("worker", "cli"),
                False,
                "shapes",
            )
        )
    if nightly():
        big = {
            "type": "FeatureCollection",
            "features": [
                _feature([_geo_ring(_square(float(i), float(i), 0.5))], label=i) for i in range(20_000)
            ],
        }
        cases.append(
            Case(
                "echo_geojson/many-20k",
                "echo_geojson",
                {"geojson": JsonFile("big.geojson", big)},
                Expect(outputs={"shapes": OutShapes(big)}),
                ("worker",),
                True,
                "shapes",
            )
        )
    bad_collections = {
        "not-a-collection": {"type": "Feature", "properties": {}, "geometry": None},
        "features-not-a-list": {"type": "FeatureCollection", "features": {}},
        "point-feature": {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [1, 2]}}
            ],
        },
        "geometry-less-feature": {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}}],
        },
        "nan-coordinate": {
            "type": "FeatureCollection",
            "features": [_feature([[[0.0, 0.0], [float("nan"), 1.0], [1.0, 1.0], [0.0, 0.0]]])],
        },
        "inf-coordinate": {
            "type": "FeatureCollection",
            "features": [_feature([[[0.0, 0.0], [float("inf"), 1.0], [1.0, 1.0], [0.0, 0.0]]])],
        },
        "text-coordinate": {
            "type": "FeatureCollection",
            "features": [_feature([[["a", "b"], [1.0, 1.0], [2.0, 2.0], ["a", "b"]]])],
        },
        "feature-is-a-number": {"type": "FeatureCollection", "features": [5]},
    }
    for name, collection in bad_collections.items():
        cases.append(
            Case(
                "echo_geojson/invalid/%s" % name,
                "echo_geojson",
                {"geojson": JsonFile("bad.geojson", collection)},
                Expect(status="FAILED", code="bad_return", toolerror=True),
                ("worker",),
                False,
                "shapes",
            )
        )
    # polygons given as [y, x] vertices: the output is closed GeoJSON [x, y]
    triangle = [[0.0, 0.0], [0.0, 8.0], [5.0, 3.0]]
    lists = {
        "triangle": ([triangle], [_feature([_geo_ring(triangle)])]),
        "square-already-closed": (
            [_square(1.0, 2.0, 3.0) + [[1.0, 2.0]]],
            [_feature([_geo_ring(_square(1.0, 2.0, 3.0))])],
        ),
        "yx-order-asymmetric": (
            [[[1.0, 100.0], [2.0, 200.0], [3.0, 150.0]]],
            [_feature([[[100.0, 1.0], [200.0, 2.0], [150.0, 3.0], [100.0, 1.0]]])],
        ),
        "with-properties": (
            [{"polygon": triangle, "label": 4, "name": "t \u00e9"}],
            [_feature([_geo_ring(triangle)], label=4, name="t \u00e9")],
        ),
        "many-100": (
            [_square(float(i), float(i), 1.0) for i in range(100)],
            [_feature([_geo_ring(_square(float(i), float(i), 1.0))]) for i in range(100)],
        ),
        "none": ([], []),
        "huge": ([_square(1e15, 1e15, 1e14)], [_feature([_geo_ring(_square(1e15, 1e15, 1e14))])]),
        "integer-centres": (
            [[[0, 0], [0, 3], [2, 3]]],
            [_feature([[[0.0, 0.0], [3.0, 0.0], [3.0, 2.0], [0.0, 0.0]]])],
        ),
    }
    for name, (payload, features) in lists.items():
        collection = {"type": "FeatureCollection", "features": features}
        cases.append(
            Case(
                "echo_polygons/%s" % name,
                "echo_polygons",
                {"polygons": JsonFile("polygons.json", payload)},
                Expect(outputs={"shapes": OutShapes(collection)}),
                ("worker", "cli"),
                False,
                "shapes",
            )
        )
    bad_lists = {
        "two-vertices": [[[0.0, 0.0], [1.0, 1.0]]],
        "repeated-vertex": [[[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]]],
        "dict-without-polygon": [{"label": 1}],
        "nan-vertex": [[[0.0, 0.0], [float("nan"), 1.0], [1.0, 2.0]]],
        "wrong-width": [[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [2.0, 2.0, 2.0]]],
        "text-vertex": [[["a", "b"], ["c", "d"], ["e", "f"]]],
        "not-a-list": 5,
    }
    for name, payload in bad_lists.items():
        cases.append(
            Case(
                "echo_polygons/invalid/%s" % name,
                "echo_polygons",
                {"polygons": JsonFile("bad.json", payload)},
                Expect(status="FAILED", code="bad_return", toolerror=True),
                ("worker",),
                False,
                "shapes",
            )
        )
    return cases


def outline_cases() -> list[Case]:
    rng = np.random.default_rng(RNG_SEED + 3)
    cases: list[Case] = []
    shapes: dict[str, np.ndarray] = {}
    one = np.zeros((5, 7), np.uint8)
    one[2, 3] = 1
    shapes["single-pixel"] = one
    square = np.zeros((8, 9), np.uint8)
    square[1:4, 2:5] = 1
    shapes["square-3x3"] = square
    ring = np.zeros((9, 9), np.uint8)
    ring[1:8, 1:8] = 1
    ring[3:6, 3:6] = 0
    shapes["label-with-a-hole"] = ring
    island = ring.copy()
    island[4, 4] = 1  # an object inside the hole of another label: keep it as its own label
    island[4, 4] = 2
    shapes["island-inside-a-hole"] = island
    diagonal = np.zeros((6, 6), np.uint8)
    diagonal[1, 1] = 1
    diagonal[2, 2] = 1
    diagonal[4, 4] = 1
    shapes["parts-touching-diagonally"] = diagonal
    two = np.zeros((6, 10), np.uint16)
    two[1:4, 1:4] = 1
    two[1:4, 4:8] = 2  # touching labels share an edge
    two[5, 9] = 3
    shapes["touching-labels"] = two
    border = np.zeros((5, 5), np.uint8)
    border[0, :] = 1
    border[:, 4] = 2
    shapes["touching-the-image-border"] = border
    shapes["wide-1xN"] = np.array([[0, 1, 1, 1, 0, 2]], np.uint8)
    shapes["tall-Nx1"] = np.array([[1], [1], [0], [3]], np.uint8)
    blobs = np.zeros((64, 64), np.uint16)
    for k in range(1, 9):
        y, x = rng.integers(4, 56, size=2)
        h, w = rng.integers(2, 9, size=2)
        blobs[y : y + h, x : x + w] = k
    shapes["random-blobs-64x64"] = blobs
    noise = (rng.random((20, 20)) > 0.6).astype(np.uint8)
    shapes["salt-noise"] = noise
    for name, labels in shapes.items():
        cases.append(
            Case(
                "outline_labels/%s" % name,
                "outline_labels",
                {"labels": labels},
                Expect(outputs={"shapes": OutOutlines(labels)}),
                ("worker", "cli"),
                False,
                "shapes",
            )
        )
    cases.append(
        Case(
            "outline_labels/min-area-skips-small-labels",
            "outline_labels",
            {"labels": two, "min_area": 5},
            Expect(outputs={"shapes": OutOutlines(two, min_area=5)}),
            ("worker", "cli"),
            False,
            "shapes",
        )
    )
    cases.append(
        Case(
            "outline_labels/min-area-drops-everything",
            "outline_labels",
            {"labels": two, "min_area": 1000},
            Expect(outputs={"shapes": OutOutlines(two, min_area=1000)}),
            ("worker",),
            False,
            "shapes",
        )
    )
    cases.append(
        Case(
            "outline_labels/simplified",
            "outline_labels",
            {"labels": blobs, "simplify": 0.5},
            Expect(outputs={"shapes": OutOutlines(blobs, simplify=0.5, slack=int(blobs.size * 0.02))}),
            ("worker",),
            False,
            "shapes",
        )
    )
    cases.append(
        Case(
            "outline_labels/all-background",
            "outline_labels",
            {"labels": np.zeros((4, 4), np.uint8)},
            Expect(outputs={"shapes": OutOutlines(np.zeros((4, 4), np.uint8))}),
            ("worker",),
            False,
            "shapes",
        )
    )
    cases.append(
        Case(
            "outline_labels/not-2d",
            "outline_labels",
            {"labels": np.ones((2, 3, 3), np.uint8)},
            Expect(status="FAILED", code="bad_input", toolerror=True),
            ("worker",),
            False,
            "shapes",
        )
    )
    cases.append(
        Case(
            "outline_labels/min-area-below-minimum",
            "outline_labels",
            {"labels": one, "min_area": 0},
            Expect(status="FAILED", code="invalid_parameter", toolerror=True),
            ("worker",),
            False,
            "shapes",
        )
    )
    return cases


# --------------------------------------------------------------------------------------------------------- affine
def affine_cases() -> list[Case]:
    cases: list[Case] = []
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    good = {
        "identity": (identity, identity),
        "translation": (
            [[1, 0, 5], [0, 1, -3], [0, 0, 1]],
            [[1.0, 0.0, 5.0], [0.0, 1.0, -3.0], [0.0, 0.0, 1.0]],
        ),
        "rotation-asymmetric": (
            [[0.0, -1.0, 2.0], [1.0, 0.0, 7.0], [0.0, 0.0, 1.0]],
            [[0.0, -1.0, 2.0], [1.0, 0.0, 7.0], [0.0, 0.0, 1.0]],
        ),
        "two-by-three-completed": (
            [[2, 0, 1], [0, 3, 4]],
            [[2.0, 0.0, 1.0], [0.0, 3.0, 4.0], [0.0, 0.0, 1.0]],
        ),
        "huge-and-tiny": (
            [[1e300, 0, 5e-324], [0, 1e-300, 0], [0, 0, 1]],
            [[1e300, 0.0, 5e-324], [0.0, 1e-300, 0.0], [0.0, 0.0, 1.0]],
        ),
        "negative-zero": (
            [[-0.0, 0.0, 0.0], [0.0, 1.0, -0.0], [0.0, 0.0, 1.0]],
            [[-0.0, 0.0, 0.0], [0.0, 1.0, -0.0], [0.0, 0.0, 1.0]],
        ),
    }
    for name, (given, expected) in good.items():
        text = json.dumps(given)
        cases.append(
            Case(
                "echo_affine/%s" % name,
                "echo_affine",
                {"matrix_json": text},
                Expect(outputs={"affine": OutAffine(expected)}),
                ("worker", "cli", "snippet"),
                False,
                "affine",
            )
        )
        cases.append(
            Case(
                "echo_affine_applied/%s" % name,
                "echo_affine_applied",
                {"matrix_json": text},
                Expect(
                    outputs={
                        "affine": OutAffine(expected, {"apply_to": "source", "relative_to": "reference"})
                    }
                ),
                ("worker",),
                False,
                "affine",
            )
        )
    for name, text in {
        "four-by-four": json.dumps([[1, 0, 0, 0]] * 4),
        "three-by-two": json.dumps([[1, 0]] * 3),
        "one-row": json.dumps([[1, 0, 0]]),
        "flat": json.dumps([1, 0, 0, 0, 1, 0, 0, 0, 1]),
    }.items():
        cases.append(
            Case(
                "echo_affine/invalid/%s" % name,
                "echo_affine",
                {"matrix_json": text},
                Expect(status="FAILED", code="bad_return", toolerror=True),
                ("worker",),
                False,
                "affine",
            )
        )
    for name, text in {
        "ragged": json.dumps([[1, 0, 0], [0, 1], [0, 0, 1]]),
        "text-cell": json.dumps([["a", 0, 0], [0, 1, 0], [0, 0, 1]]),
    }.items():
        cases.append(
            Case(
                "echo_affine/invalid/%s" % name,
                "echo_affine",
                {"matrix_json": text},
                Expect(status="FAILED", code="bad_return", toolerror=True),
                ("worker",),
                False,
                "affine",
            )
        )
    for name, text in {
        "nan": "[[1, 0, NaN], [0, 1, 0], [0, 0, 1]]",
        "inf": "[[1, 0, Infinity], [0, 1, 0], [0, 0, 1]]",
    }.items():
        cases.append(
            Case(
                "echo_affine/invalid/%s-cell" % name,
                "echo_affine",
                {"matrix_json": text},
                Expect(status="FAILED", code="bad_return", toolerror=True),
                ("worker",),
                False,
                "affine",
            )
        )
    return cases


# -------------------------------------------------------------------------------------------- messages and scalars out
MESSAGES: dict[str, str] = {
    "plain": "Hello",
    "bold-and-list": "**Result**\n- one\n- two",
    "unicode": "caf\u00e9 \u00b5m \U0001f600 \u65e5\u672c\u8a9e",
    "inner-newlines-and-tabs": "a\n\nb\tc",
    "quotes": 'it\'s "quoted" \\ back',
    "surrounded-by-whitespace": "  \n padded \t ",
    "crlf": "x\r\ny",
    "long-100k": "m" * 100_000,
}


def message_cases() -> list[Case]:
    cases: list[Case] = []
    for name, text in MESSAGES.items():
        cases.append(
            Case(
                "echo_message/%s" % name,
                "echo_message",
                {"text": text},
                Expect(outputs={"message": OutText(text.strip())}),
                ("worker", "cli", "snippet"),
                False,
                "message",
            )
        )
    for name, text in {
        "empty": "",
        "spaces": "   ",
        "newlines": "\n\n",
        "tabs-and-nbsp": "\t\u00a0 ",
    }.items():
        cases.append(
            Case(
                "echo_message/invalid/%s" % name,
                "echo_message",
                {"text": text},
                Expect(status="FAILED", code="bad_return", toolerror=True),
                ("worker",),
                False,
                "message",
            )
        )
    return cases


def scalars_out_cases() -> list[Case]:
    f32 = float(np.float32(0.1))
    return [
        Case(
            "typed_scalars/numpy",
            "typed_scalars",
            {"kind": "numpy"},
            Expect(received={"i64": 2**40, "u8": 200, "f32": f32, "f64": 0.1, "bool": True, "zero_d": 3}),
            ("worker", "cli", "snippet"),
            False,
            "scalars-out",
        ),
        Case(
            "typed_scalars/nan-and-inf-become-null",
            "typed_scalars",
            {"kind": "nan"},
            Expect(received={"nan": None, "inf": None, "ninf": None, "ok": 1.5, "np_nan": None}),
            ("worker", "cli", "snippet"),
            False,
            "scalars-out",
        ),
        Case(
            "typed_scalars/nested",
            "typed_scalars",
            {"kind": "nested"},
            Expect(received={"list": [1, None, [2, None]], "dict": {"a": None, "b": [1, 2]}}),
            ("worker", "cli"),
            False,
            "scalars-out",
        ),
    ]


# -------------------------------------------------------------------------------------------- files and folders
def _file_names() -> dict[str, str]:
    names = {
        "plain": "plain.txt",
        "with-space": "with space.txt",
        "unicode": "\u00fcn\u00ef\u00a9ode \u2713 \u65e5\u672c.bin",
        "emoji": "emoji \U0001f600.dat",
        "single-quote": "it's.txt",
        "shell-metacharacters": "a;b&c$d`e(f)g.txt",
        "percent-and-hash": "100% #1 [x] {y}.txt",
        "leading-dash": "-dash.txt",
        "equals": "a=b.txt",
        "long-name": "n" * 120 + ".txt",
        "several-dots": "a.b.c.tar.gz",
        "tilde": "~tilde.txt",
    }
    if os.name != "nt":  # characters Windows file names cannot hold
        names["double-quote"] = 'say "hi".txt'
        names["trailing-space"] = "trailing space .txt"
        names["backslash"] = "back\\slash.txt"
        names["newline"] = "new\nline.txt"
    return names


def file_cases() -> list[Case]:
    cases: list[Case] = []
    content = bytes(range(256)) * 3 + "text \u00e9\n".encode()
    for label, name in _file_names().items():
        digest = hashlib.sha256(content).hexdigest()
        expected = Expect(
            received={
                "name": name,
                "str": SentPath("file"),
                "exists": True,
                "size": len(content),
                "digest": digest,
                "type": "PosixPath" if os.name != "nt" else "WindowsPath",
            },
            outputs={"file": OutFile(digest, "file")},
        )
        cases.append(
            Case(
                "echo_file/name/%s" % label,
                "echo_file",
                {"file": FileSpec(name, content)},
                expected,
                ("worker", "cli", "snippet") if "\n" not in name else ("worker",),
                False,
                "file",
            )
        )
    empty = hashlib.sha256(b"").hexdigest()
    cases.append(
        Case(
            "echo_file/empty-file",
            "echo_file",
            {"file": FileSpec("empty.bin", b"")},
            Expect(
                received={"name": "empty.bin", "exists": True, "size": 0, "digest": empty},
                outputs={"file": OutFile(empty, "file")},
            ),
            ("worker", "cli", "snippet"),
            False,
            "file",
        )
    )
    mid = bytes(np.random.default_rng(RNG_SEED).integers(0, 256, size=3_000_000, dtype=np.uint8))
    cases.append(
        Case(
            "echo_file/3MB",
            "echo_file",
            {"file": FileSpec("three_mb.bin", mid)},
            Expect(
                received={"size": len(mid), "digest": hashlib.sha256(mid).hexdigest()},
                outputs={"file": OutFile(hashlib.sha256(mid).hexdigest(), "file")},
            ),
            ("worker",),
            False,
            "file",
        )
    )
    if nightly():
        huge = bytes(np.random.default_rng(RNG_SEED + 1).integers(0, 256, size=64_000_000, dtype=np.uint8))
        cases.append(
            Case(
                "echo_file/64MB",
                "echo_file",
                {"file": FileSpec("sixty_four_mb.bin", huge)},
                Expect(
                    received={"size": len(huge), "digest": hashlib.sha256(huge).hexdigest()},
                    outputs={"file": OutFile(hashlib.sha256(huge).hexdigest(), "file")},
                ),
                ("worker",),
                True,
                "file",
            )
        )
    # a path that does not exist: a File is only a path, the tool is told it is not there
    cases.append(
        Case(
            "echo_file/missing",
            "echo_file",
            {"file": MissingPath("not_there.txt")},
            Expect(
                received={"name": "not_there.txt", "exists": False, "size": None, "digest": None},
                outputs={"file": OutFile(None, "file")},
            ),
            ("worker",),
            False,
            "file",
        )
    )

    entries = (("a.txt", b"1"), ("b b.txt", b"22"), ("\u00fcn.txt", b""), (".hidden", b"x"))
    folder_names = {
        "plain": "plain_folder",
        "with-space": "folder with space",
        "unicode": "d\u00e4t\u00e4 \u2713 \u65e5\u672c",
        "emoji": "dir \U0001f600",
        "single-quote": "it's folder",
        "shell-metacharacters": "a;b&c$d`e",
    }
    for label, name in folder_names.items():
        expected = Expect(
            received={"name": name, "str": SentPath("folder"), "entries": sorted(n for n, _ in entries)},
            outputs={"folder": OutFile(None, "folder")},
        )
        cases.append(
            Case(
                "echo_folder/name/%s" % label,
                "echo_folder",
                {"folder": FolderSpec(name, entries)},
                expected,
                ("worker", "cli", "snippet"),
                False,
                "folder",
            )
        )
    cases.append(
        Case(
            "echo_folder/empty-folder",
            "echo_folder",
            {"folder": FolderSpec("empty_folder")},
            Expect(received={"entries": []}, outputs={"folder": OutFile(None, "folder")}),
            ("worker", "cli", "snippet"),
            False,
            "folder",
        )
    )
    many = tuple(("f%04d.txt" % i, b"") for i in range(1000))
    cases.append(
        Case(
            "echo_folder/1000-entries",
            "echo_folder",
            {"folder": FolderSpec("many", many)},
            Expect(
                received={"entries": sorted(n for n, _ in many)}, outputs={"folder": OutFile(None, "folder")}
            ),
            ("worker",),
            False,
            "folder",
        )
    )
    cases.append(
        Case(
            "echo_folder/missing",
            "echo_folder",
            {"folder": MissingPath("no_such_folder")},
            Expect(status="FAILED", code="folder_not_found", toolerror=True, message="no_such_folder"),
            ("worker", "cli"),
            False,
            "folder",
        )
    )
    cases.append(
        Case(
            "echo_folder/is-a-file",
            "echo_folder",
            {"folder": FileSpec("i_am_a_file.txt", b"x")},
            Expect(status="FAILED", code="folder_not_found", toolerror=True),
            ("worker",),
            False,
            "folder",
        )
    )
    return cases


# --------------------------------------------------------------------------------------------------- transforms
def transform_cases() -> list[Case]:
    cases: list[Case] = []
    rng = np.random.default_rng(RNG_SEED + 2)
    # image + 1 in float32: the oracle is numpy's own arithmetic on the float32 view of the input
    for dtype in ("uint8", "uint16", "int16", "float32", "float64", "bool"):
        for name in ("1x1", "2x3", "64x64", "3d-3x4x5"):
            a = ramp(SHAPES[name], dtype)
            expected = a.astype(np.float32) + np.float32(1)
            cases.append(
                Case(
                    "image_plus_one/%s/%s" % (dtype, name),
                    "image_plus_one",
                    {"image": a},
                    Expect(outputs={"image": OutImage(expected, ("float32",))}),
                    ("worker", "cli", "snippet") if a.size <= 4096 else ("worker",),
                    False,
                    "transform",
                )
            )
    a = np.array([[255, 0, 254]], dtype=np.uint8)
    cases.append(
        Case(
            "image_plus_one/uint8-255-does-not-wrap",
            "image_plus_one",
            {"image": a},
            Expect(outputs={"image": OutImage(np.array([[256.0, 1.0, 255.0]], np.float32), ("float32",))}),
            ("worker", "cli"),
            False,
            "transform",
        )
    )
    a = np.array([[np.nan, np.inf, -np.inf, -0.0]], dtype=np.float32)
    cases.append(
        Case(
            "image_plus_one/float32-specials",
            "image_plus_one",
            {"image": a},
            Expect(
                outputs={
                    "image": OutImage(np.array([[np.nan, np.inf, -np.inf, 1.0]], np.float32), ("float32",))
                }
            ),
            ("worker",),
            False,
            "transform",
        )
    )
    # column sum
    frames = {
        "ints": (pd.DataFrame({"a": [1, 2, 3, 4], "b": [10, 20, 30, 40]}), "b", 100.0),
        "floats": (pd.DataFrame({"a": [0.5, 0.25, 0.125]}), "a", 0.875),
        "negative": (pd.DataFrame({"a": [-5, 5, -7]}), "a", -7.0),
        "unicode-column": (pd.DataFrame({"\u00b5m": [1, 2, 3]}), "\u00b5m", 6.0),
        "one-row": (pd.DataFrame({"a": [42]}), "a", 42.0),
        "empty": (pd.DataFrame({"a": pd.Series([], dtype="float64")}), "a", 0.0),
        "big-ints": (pd.DataFrame({"a": [2**40, 2**41]}), "a", float(2**40 + 2**41)),
    }
    for name, (frame, column, total) in frames.items():
        cases.append(
            Case(
                "table_column_sum/%s" % name,
                "table_column_sum",
                {"table": frame, "column": column},
                Expect(received={"sum": total, "n_rows": len(frame)}),
                ("worker", "cli"),
                False,
                "transform",
            )
        )
    cases.append(
        Case(
            "table_column_sum/no-such-column",
            "table_column_sum",
            {"table": pd.DataFrame({"a": [1]}), "column": "b"},
            Expect(status="FAILED", code="no_column", toolerror=True),
            ("worker",),
            False,
            "transform",
        )
    )
    # label count and areas
    for name, labels in {
        "three-objects": np.array([[0, 1, 1, 0], [2, 2, 0, 3], [0, 0, 0, 3]], np.uint16),
        "all-background": np.zeros((4, 4), np.uint8),
        "single-pixel": np.array([[7]], np.int32),
        "gaps-in-numbering": np.array([[5, 0, 100], [100, 100, 5]], np.uint16),
        "random-64x64": rng.integers(0, 12, size=(64, 64)).astype(np.uint8),
        "3d": rng.integers(0, 4, size=(3, 5, 6)).astype(np.uint8),
    }.items():
        values, counts = np.unique(labels[labels != 0], return_counts=True)
        areas = {str(int(v)): int(c) for v, c in zip(values, counts)}
        cases.append(
            Case(
                "count_labels/%s" % name,
                "count_labels",
                {"labels": labels},
                Expect(received={"count": len(areas), "areas": areas}),
                ("worker", "cli") if labels.size <= 4096 else ("worker",),
                False,
                "transform",
            )
        )
    # region box: the bounding box of the non-zero pixels, numpy's own answer
    image = np.arange(7 * 9, dtype=np.uint16).reshape(7, 9)
    masks: dict[str, np.ndarray] = {}
    m = np.zeros((7, 9), np.uint8)
    m[2:5, 3:8] = 1
    masks["rectangle"] = m
    m = np.zeros((7, 9), np.uint8)
    m[0, 0] = 1
    masks["top-left-pixel"] = m
    m = np.zeros((7, 9), np.uint8)
    m[6, 8] = 3
    masks["bottom-right-pixel"] = m
    m = np.zeros((7, 9), np.uint8)
    m[1, 8] = 1
    m[5, 0] = 2
    masks["two-far-corners"] = m
    masks["whole-image"] = np.ones((7, 9), np.uint8)
    for name, mask in masks.items():
        rows, cols = np.nonzero(mask)
        expected = {
            "rows": [int(rows.min()), int(rows.max()) + 1],
            "columns": [int(cols.min()), int(cols.max()) + 1],
        }
        cases.append(
            Case(
                "region_box/%s" % name,
                "region_box",
                {"image": image, "region": mask},
                Expect(received=expected),
                ("worker", "cli"),
                False,
                "transform",
            )
        )
    cases.append(
        Case(
            "region_box/no-region-is-the-whole-image",
            "region_box",
            {"image": image},
            Expect(received={"rows": [0, 7], "columns": [0, 9]}),
            ("worker", "cli", "snippet"),
            False,
            "transform",
        )
    )
    cube = np.zeros((3, 7, 9), np.uint16)
    cases.append(
        Case(
            "region_box/3d-image-2d-region",
            "region_box",
            {"image": cube, "region": masks["rectangle"]},
            Expect(received={"rows": [2, 5], "columns": [3, 8]}),
            ("worker",),
            False,
            "transform",
        )
    )
    cases.append(
        Case(
            "region_box/empty-region",
            "region_box",
            {"image": image, "region": np.zeros((7, 9), np.uint8)},
            Expect(status="FAILED", code="empty_region", toolerror=True),
            ("worker",),
            False,
            "transform",
        )
    )
    cases.append(
        Case(
            "region_box/wrong-size",
            "region_box",
            {"image": image, "region": np.ones((7, 8), np.uint8)},
            Expect(status="FAILED", code="bad_input", toolerror=True),
            ("worker",),
            False,
            "transform",
        )
    )
    cases.append(
        Case(
            "region_box/region-3d",
            "region_box",
            {"image": image, "region": np.ones((2, 7, 9), np.uint8)},
            Expect(status="FAILED", code="bad_input", toolerror=True),
            ("worker",),
            False,
            "transform",
        )
    )
    return cases


# ------------------------------------------------------------------------------------------------------ assembly
@functools.lru_cache(maxsize=1)
def all_cases() -> tuple[Case, ...]:
    """Every case, deterministic order. Ids are unique."""
    cases: list[Case] = []
    for generator in (
        image_cases, labels_cases, outline_cases, _scalar_cases, _choice_cases, _default_cases, _nullable_cases, _bound_cases,
        table_cases, points_cases, shapes_cases, affine_cases, message_cases, scalars_out_cases, file_cases, transform_cases,
    ):  # fmt: skip
        cases.extend(generator())
    return tuple(cases)


def profile() -> str:
    """`ci` (default) or `nightly` (LC_ROUNDTRIP_PROFILE=nightly): the nightly one adds the heavy cases and every transport."""
    return os.environ.get("LC_ROUNDTRIP_PROFILE", "ci")


def nightly() -> bool:
    return profile() == "nightly"


# How many cases of each group ride each slow transport in the `ci` profile (the worker protocol always carries them all):
# a command line or a copied snippet starts two Python processes per case. Cases are picked evenly along the group, the
# nightly profile sends every case that can travel on the transport.
TRANSPORT_LIMITS: dict[str, dict[str, int]] = {
    "cli": {
        "string": 45,
        "int": 8,
        "float": 8,
        "choice": 8,
        "file": 12,
        "folder": 6,
        "image": 8,
        "_default": 4,
    },
    "terminal": {"string": 25, "int": 3, "float": 3, "choice": 3, "file": 6, "folder": 3, "_default": 2},
    "snippet": {"string": 12, "int": 3, "float": 3, "choice": 3, "file": 4, "folder": 3, "_default": 3},
    "notebook": {"string": 25, "int": 25, "float": 25, "choice": 20, "_default": 10},
}


def _thin(cases: list[Case], limit: int) -> list[Case]:
    if len(cases) <= limit:
        return cases
    return [cases[(i * len(cases)) // limit] for i in range(limit)]


@functools.lru_cache(maxsize=8)
def selected(path: str | None = None, prof: str | None = None) -> tuple[Case, ...]:
    """The cases of this profile that travel on `path` (all of them when None)."""
    prof = prof or profile()
    carried_by = (
        "cli" if path == "terminal" else path
    )  # the copied terminal line carries what the command line carries
    pool = [
        c
        for c in all_cases()
        if (prof == "nightly" or not c.heavy) and (carried_by is None or carried_by in c.paths)
    ]
    if path is None or path == "worker" or prof == "nightly":
        return tuple(pool)
    limits = TRANSPORT_LIMITS[path]
    groups: dict[str, list[Case]] = {}
    for case in pool:
        groups.setdefault(case.group, []).append(case)
    picked = [
        c for group, members in groups.items() for c in _thin(members, limits.get(group, limits["_default"]))
    ]
    return tuple(picked)
