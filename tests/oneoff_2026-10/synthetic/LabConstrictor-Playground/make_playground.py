#!/usr/bin/env python3
"""Synthetic datasets for the LabConstrictor Playground tools (derived from the declared inputs of each tool).

    python make_playground.py OUT_DIR       # standalone: numpy, scipy, pandas, tifffile; common.py and check_ground_truth.py next to it or one folder up

Image datasets are in `pg_images.py`; this file holds the tables, the files and the data-making tool, and the entry point.
Tools without data (`check_everything`, `list_devices`, `run_on_device`, the stress tools that make their own data) need no dataset.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import Suite, chk_files, chk_status, chk_table, chk_value, standalone_main  # noqa: E402
from pg_images import build_images  # noqa: E402

APP, VERSION = "LabConstrictor-Playground", "0.0.4"
LIMIT = 1_000_000  # MAX_FILE_BYTES of the tool 'Look inside a file'


def summary_rows(table: pd.DataFrame) -> list[dict[str, Any]]:
    """count/mean/min/max of every numeric column, with plain Python (math.fsum), as the truth of 'Summarise a table'."""
    rows: list[dict[str, Any]] = []
    for name in table.columns:
        if not pd.api.types.is_numeric_dtype(table[name]):
            continue
        cells = [float(v) for v in table[name] if not math.isnan(v)]
        rows.append(
            {
                "column": str(name),
                "count": len(cells),
                "mean": math.fsum(cells) / len(cells),
                "min": min(cells),
                "max": max(cells),
            }
        )
    return rows


def add_tables(s: Suite) -> None:
    def table_case(
        ident: str, purpose: str, table: pd.DataFrame, derivation: str, raw_name: str | None = None
    ) -> None:
        path = s.fixtures / (ident + ".csv")
        table.to_csv(path, index=False)
        rows = summary_rows(table)
        truth = s.out / "truth" / (ident + "_summary.csv")
        truth.parent.mkdir(exist_ok=True)
        pd.DataFrame(rows).to_csv(truth, index=False)
        cells = {
            "%s[%d]" % (col, i): rows[i][col] for i in range(min(2, len(rows))) for col in ("mean", "max")
        }
        s.dataset(
            ident,
            purpose,
            "works",
            derivation=derivation,
            files=[path, truth],
            tool="summarise_table",
            inputs={"table": s.rel(path)},
            expect={
                "results": {
                    "summary": {
                        "columns": ["column", "count", "mean", "min", "max"],
                        "rows": len(rows),
                        "cells": cells,
                    },
                    "values": {"rows": len(table), "columns": table.shape[1], "numeric_columns": len(rows)},
                }
            },
            checks=[
                chk_status("COMPLETE"),
                chk_table(
                    "summary",
                    "column",
                    s.rel(truth),
                    ["count", "mean", "min", "max"],
                    rtol=1e-9,
                    atol=1e-9,
                    rows=len(rows),
                ),
                chk_value("rows", len(table)),
                chk_value("columns", table.shape[1]),
                chk_value("numeric_columns", len(rows)),
            ],
        )

    n = 8
    basic = pd.DataFrame(
        {
            "id": range(1, n + 1),
            "a": [float(v) for v in range(1, n + 1)],
            "b": [5.0] * n,
            "c": [2.0, None, 4.0, 6.0, None, 10.0, 12.0, 14.0],
            "name": list("abcdefgh"),
        }
    )
    table_case(
        "pg_table_basic",
        "8 rows: a counter, a constant, a column with 2 empty cells, a text column",
        basic,
        "id and a: 1..8 (mean 4.5, min 1, max 8, count 8); b: 5 everywhere; c: the 6 non-empty cells 2,4,6,10,12,14 (count 6, mean 8); the text column is not summarised.",
    )
    unicode = pd.DataFrame(
        {"longueur µm": [1.5, 2.5, 3.5], "größe": [10, 20, 60], "наблюдения": [0.1, 0.2, 0.6]}
    )
    table_case(
        "pg_table_unicode",
        "column names with µ, ß and Cyrillic",
        unicode,
        "Means 2.5, 30, 0.3; the names must survive unchanged.",
    )
    rng = np.random.default_rng(404)
    big = pd.DataFrame(
        {
            "x": rng.normal(100, 15, 100_000),
            "y": rng.integers(0, 1000, 100_000).astype(float),
            "z": rng.uniform(-1, 1, 100_000),
        }
    )
    table_case(
        "pg_table_big",
        "stress: 100 000 rows x 3 numeric columns",
        big,
        "Count, mean (math.fsum), min and max computed in plain Python from the same values.",
    )
    text = pd.DataFrame({"name": ["a", "b", "c"], "kind": ["x", "y", "z"]})
    path = s.fixtures / "pg_table_no_numbers.csv"
    text.to_csv(path, index=False)
    s.dataset(
        "pg_table_no_numbers",
        "a table with only text columns",
        "refused",
        derivation="Nothing to summarise.",
        files=[path],
        tool="summarise_table",
        inputs={"table": s.rel(path)},
        expect={"status": "FAILED", "code": "no_numbers", "message_contains": "no column of numbers"},
        checks=[chk_status("FAILED", "no_numbers", "no column of numbers")],
        outcome_text="refused: no_numbers",
    )
    header = s.fixtures / "pg_table_header_only.csv"
    header.write_text("a,b,c\n", encoding="utf-8")
    s.dataset(
        "pg_table_header_only",
        "a header and no rows",
        "refused",
        derivation="No data: there is nothing to summarise (a table of NaN statistics would be a silent wrong result).",
        files=[header],
        tool="summarise_table",
        inputs={"table": s.rel(header)},
        expect={"status": "FAILED"},
        checks=[chk_status("FAILED")],
        outcome_text="refused with a sentence",
    )


def add_files(s: Suite) -> None:
    def file_case(
        ident: str,
        purpose: str,
        raw: bytes,
        outcome: str,
        values: dict | None = None,
        code: str | None = None,
        contains: str | None = None,
        derivation: str = "",
        name: str = "",
    ) -> None:
        path = s.fixtures / (name or ident + ".txt")
        path.write_bytes(raw)
        if outcome == "works":
            assert values is not None
            s.dataset(
                ident,
                purpose,
                outcome,
                derivation=derivation,
                files=[path],
                tool="look_inside_file",
                inputs={"file": s.rel(path)},
                expect={"results": {"values": values}},
                checks=[chk_status("COMPLETE")] + [chk_value(k, v) for k, v in values.items()],
            )
        else:
            s.dataset(
                ident,
                purpose,
                outcome,
                derivation=derivation,
                files=[path],
                tool="look_inside_file",
                inputs={"file": s.rel(path)},
                expect={"status": "FAILED", "code": code, "message_contains": contains},
                checks=[chk_status("FAILED", code, contains)],
                outcome_text="refused: %s" % code,
            )

    doc = {
        "name": "synthetic µ→✓",
        "threshold": 0.25,
        "channels": 4,
        "normalise": False,
        "nested": {"a": 1},
        "tags": [1, 2],
    }
    file_case(
        "pg_file_json",
        "a JSON object with text, numbers, a boolean, a nested object and a list",
        json.dumps(doc, ensure_ascii=False).encode("utf-8"),
        "works",
        {
            "kind": "json",
            "keys": "channels, name, nested, normalise, tags, threshold",
            "value_name": "synthetic µ→✓",
            "value_threshold": 0.25,
            "value_channels": 4,
            "value_normalise": False,
            "bytes": len(json.dumps(doc, ensure_ascii=False).encode("utf-8")),
        },
        derivation="Keys sorted; plain values (text, number, boolean) reported as value_<key>; the nested object and the list are not. bytes = the UTF-8 size of the file.",
        name="pg_file_json.json",
    )
    file_case(
        "pg_file_json_list",
        "a JSON list",
        b"[1, 2, 3]",
        "works",
        {"kind": "json", "file": "pg_file_json_list.txt"},
        derivation="Valid JSON that is not an object: kind json, no keys.",
    )
    file_case(
        "pg_file_text_crlf",
        "three lines with CRLF, LF and a trailing newline",
        b"alpha\r\nbeta\ngamma\n",
        "works",
        {"kind": "text", "lines": 3, "bytes": 18},
        derivation="Three lines whatever the line ends.",
    )
    file_case(
        "pg_file_empty",
        "an empty file",
        b"",
        "works",
        {"kind": "text", "lines": 0, "bytes": 0},
        derivation="0 bytes: not JSON, 0 lines.",
    )
    file_case(
        "pg_file_exact_limit",
        "a text file of exactly 1 000 000 bytes",
        (b"a" * 99 + b"\n") * 10_000,
        "works",
        {"kind": "text", "lines": 10_000, "bytes": LIMIT},
        derivation="The limit is 'at most 1 MB': the boundary itself must be accepted (an off-by-one would refuse it).",
    )
    file_case(
        "pg_file_over_limit",
        "a text file of 1 000 001 bytes",
        (b"a" * 99 + b"\n") * 10_000 + b"b",
        "refused",
        code="file_too_large",
        contains="1000001 bytes",
        derivation="One byte over the limit.",
    )
    binary = bytes(np.random.default_rng(5).integers(128, 256, 4096, dtype=np.uint8))
    file_case(
        "pg_file_binary",
        "a binary file (bytes 128-255)",
        binary,
        "refused",
        code="not_text",
        contains="not a UTF-8 text file",
        derivation="High bytes are not valid UTF-8.",
        name="pg_file_binary.bin",
    )


def add_make_data(s: Suite) -> None:
    out = s.fixtures / "pg_make_out"
    out.mkdir(exist_ok=True)
    (out / ".keep").write_text("", encoding="utf-8")
    s.dataset(
        "pg_make_three_channels",
        "'Make test data' kind three_channels: the docstring says the channels have the means 10, 20 and 30",
        "works",
        derivation="The tool's own declared claim: 'a 3-channel image whose channels have the means 10, 20 and 30'. Run it in a COPY of the folder (it writes into fixtures/pg_make_out).",
        files=[out / ".keep"],
        tool="make_test_data",
        inputs={"folder": s.rel(out), "kind": "three_channels", "size": 64},
        expect={"results": {"files": {"contains": "three_channels"}}},
        checks=[
            chk_status("COMPLETE"),
            chk_files("fixtures/pg_make_out/three_channels*.tif", [10, 20, 30], 1.0, axis=0),
        ],
        outcome_text="works; each channel mean within 1 of 10/20/30 (checked on the written file)",
    )
    for ident, inputs, code, text in (
        ("pg_make_size_too_small", {"size": 16}, "invalid_parameter", "must be >="),
        ("pg_make_size_too_big", {"size": 5000}, "invalid_parameter", "must be <="),
        ("pg_make_missing_folder", {"folder": "fixtures/does_not_exist"}, None, None),
    ):
        s.dataset(
            ident,
            "Make test data with %s" % ", ".join("%s=%s" % kv for kv in inputs.items()),
            "refused",
            derivation="Outside the declared range (32..4096) or a folder that does not exist.",
            tool="make_test_data",
            inputs={"folder": s.rel(out), "kind": "all", **inputs},
            expect={"status": "FAILED", **({"code": code, "message_contains": text} if code else {})},
            checks=[chk_status("FAILED", code, text)],
            outcome_text="refused",
        )


def build(out: Path) -> Suite:
    s = Suite(APP, out, VERSION)
    (out / "truth").mkdir(exist_ok=True)
    build_images(s)
    add_tables(s)
    add_files(s)
    add_make_data(s)
    for tool in (
        "check_everything",
        "list_devices",
        "run_on_device",
        "stress_big_image",
        "stress_many_points",
        "stress_slow",
        "stress_crash",
        "stress_out_of_memory",
        "stress_real_memory",
        "stress_hang",
    ):
        s.no_case[tool] = (
            "takes no input data (it tests the machine or makes its own data): the app's own lc_tests/cases.json runs it; this suite is the data-driven part"
        )
    return s


if __name__ == "__main__":
    sys.exit(standalone_main(build, HERE, __doc__ or ""))
