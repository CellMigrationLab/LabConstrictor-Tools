"""`labconstrictor-tools test`: run tools through the real worker on small samples and check the outcome.

Two layers of checks:
* contract checks, automatic for every run that completes: the results match the declared outputs, files exist
  and open, images use a dtype every host can read, tables parse, affines are finite 3x3, values are JSON;
* expectations, optional, written by the author in a cases file (see docs/AUTHORING.md). A cases file is validated first:
  an unknown or misspelled key is an error, never a silently skipped assertion.
"""

import importlib
import json
import math
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import client
from .structures import AppSchema, CaseReport, CaseSpec, Result, ToolSchema

FIJI_SAFE_DTYPES = ("uint8", "uint16", "int16", "float32")
CANCEL_GRACE_S = 10
PATH_TYPES = ("image", "labels", "table", "file", "folder")

CASE_KEYS = {"tool", "inputs", "expect", "skip", "cancel_after_s", "comment", "_dir"}
EXPECT_KEYS = {"status", "code", "message_contains", "max_seconds", "progress_events_min", "results"}
RESULT_KEYS = {  # what may be asserted about a result of each type ("values": any key of the values, or "equals": {...})
    "image": {"shape", "dtype", "mean", "max", "n_labels"},
    "labels": {"shape", "dtype", "mean", "max", "n_labels"},
    "table": {"columns", "rows", "cells"},
    "affine": {"matrix"},
    "message": {"contains"},
    "points": {"rows", "columns"},
    "file": set(),
}


# ------------------------------------------------------------------ cases
def smoke_cases(schema: AppSchema, samples: dict[str, str]) -> list[CaseSpec]:
    """One case per tool: defaults for optional parameters, `samples` (name=path) for required files/images."""
    cases: list[CaseSpec] = []
    for tool in schema["tools"]:
        inputs: dict[str, Any] = {}
        skip = None
        for param in tool["inputs"]:
            if param["name"] in samples:
                inputs[param["name"]] = samples[param["name"]]
            elif param["required"]:
                skip = "required parameter %r has no --sample" % param["name"]
        cases.append({"tool": tool["id"], "inputs": inputs, "skip": skip})
    return cases


def load_cases(path: str | Path) -> list[CaseSpec]:
    """Read and validate a cases file (ValueError listing every problem). Relative file names are resolved later, per the
    declared parameter types (see `_resolve_paths`), relative to the folder of the cases file."""
    path = Path(path).resolve()
    cases = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        unknown = set(cases) - {"cases"}
        if unknown:
            raise ValueError(
                '%s: unknown top-level key(s) %s (a cases file is a list, or {"cases": [...]})'
                % (path.name, sorted(unknown))
            )
        cases = cases.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("%s: expected a list of cases" % path.name)
    problems = [text for i, case in enumerate(cases) for text in validate_case(case, i)]
    if problems:
        raise ValueError("%s is not a valid cases file:\n  %s" % (path.name, "\n  ".join(problems)))
    for case in cases:
        case["_dir"] = str(path.parent)
    return cases


def validate_case(case: Any, index: int) -> list[str]:
    """Every problem with the shape of one case (unknown keys at any level, wrong types)."""
    where = "case %d" % index
    if not isinstance(case, dict):
        return ["%s: must be an object" % where]
    problems = []
    if not isinstance(case.get("tool"), str):
        problems.append("%s: 'tool' (the tool id) is required" % where)
    where = "case %d (%s)" % (index, case.get("tool"))
    for key in sorted(set(case) - CASE_KEYS):
        problems.append(
            "%s: unknown key %r (allowed: %s)" % (where, key, ", ".join(sorted(CASE_KEYS - {"_dir"})))
        )
    if "inputs" in case and not isinstance(case["inputs"], dict):
        problems.append("%s: 'inputs' must be an object" % where)
    expect = case.get("expect", {})
    if not isinstance(expect, dict):
        return problems + ["%s: 'expect' must be an object" % where]
    for key in sorted(set(expect) - EXPECT_KEYS):
        problems.append(
            "%s: unknown expectation %r (allowed: %s)" % (where, key, ", ".join(sorted(EXPECT_KEYS)))
        )
    results = expect.get("results", {})
    if not isinstance(results, dict) or not all(isinstance(v, dict) for v in results.values()):
        problems.append("%s: expect.results must map result names to objects" % where)
    return problems


def _resolve_paths(case: CaseSpec, tool: ToolSchema) -> dict[str, Any]:
    """The case's inputs, with relative file names of path-typed parameters resolved against the cases file's folder.
    A text parameter is never touched, even if a file of that name happens to exist."""
    base = Path(case["_dir"]) if case.get("_dir") else None
    kinds = {p["name"]: p["type"] for p in tool["inputs"]}
    inputs = dict(case.get("inputs", {}))
    if base is not None:
        for name, value in inputs.items():
            if kinds.get(name) in PATH_TYPES and isinstance(value, str) and (base / value).exists():
                inputs[name] = str((base / value).resolve())
    return inputs


# ------------------------------------------------------------------ contract checks
def contract_problems(tool: ToolSchema, results: list[Result]) -> list[str]:
    problems: list[str] = []
    declared = [(o["name"], o["type"]) for o in tool["outputs"]]
    got = [(r.get("name"), r.get("type")) for r in results]
    if declared != got:
        problems.append("results %s do not match declared outputs %s" % (got, declared))
        return problems
    for result in results:
        problems += _result_problems(result)
    return problems


def _result_problems(result: Result) -> list[str]:
    kind, name = result["type"], result["name"]
    if kind in ("image", "labels"):
        return _image_problems(name, result)
    if kind == "table":
        return _table_problems(name, result)
    if kind == "file":
        path = Path(result["path"])
        if path.is_file():
            return []
        if path.exists():
            return ["%s: %s is a directory, not a file" % (name, path)]
        return ["%s: file %s does not exist" % (name, path)]
    if kind == "values":
        try:
            json.dumps(result["values"], allow_nan=False)
        except (TypeError, ValueError) as error:
            return ["%s: values are not plain JSON (%s)" % (name, error)]
    if kind == "message":
        return [] if isinstance(result.get("text"), str) and result["text"].strip() else ["%s: the message is empty" % name]
    if kind == "points":
        return _points_problems(name, result)
    if kind == "affine":
        matrix = result.get("matrix_yx")
        ok = (
            isinstance(matrix, list)
            and len(matrix) == 3
            and all(len(row) == 3 and all(math.isfinite(v) for v in row) for row in matrix)
        )
        return [] if ok else ["%s: affine is not a finite 3x3 matrix" % name]
    return []


def _points_problems(name: str, result: Result) -> list[str]:
    import pandas as pd

    path = Path(result["path"])
    if not path.is_file():
        return ["%s: file %s does not exist" % (name, path)]
    frame = pd.read_csv(path)
    problems = []
    if list(frame.columns[:2]) != ["y", "x"]:
        problems.append("%s: the first two columns must be y and x (got %s)" % (name, list(frame.columns[:2])))
    elif not frame[["y", "x"]].apply(lambda c: c.map(math.isfinite)).all().all():
        problems.append("%s: y and x must be finite numbers" % name)
    if result.get("n") != len(frame):
        problems.append("%s: reports %s points but the file has %d" % (name, result.get("n"), len(frame)))
    return problems


def _image_problems(name: str, result: Result) -> list[str]:
    import tifffile

    path = Path(result["path"])
    if not path.exists():
        return ["%s: image file %s does not exist" % (name, path)]
    array = tifffile.imread(path)
    problems = []
    if str(array.dtype) not in FIJI_SAFE_DTYPES:
        problems.append("%s: dtype %s cannot be opened by ImageJ" % (name, array.dtype))
    if result.get("axes") and len(result["axes"]) != array.ndim:
        problems.append("%s: axes %r do not match %dD data" % (name, result["axes"], array.ndim))
    if array.size == 0:
        problems.append("%s: image is empty" % name)
    return problems


def _table_problems(name: str, result: Result) -> list[str]:
    import pandas as pd

    try:
        frame = pd.read_csv(result["path"])
    except Exception as error:  # noqa: BLE001 - any parse failure is a finding
        return ["%s: table does not parse (%s)" % (name, error)]
    return ["%s: table has no columns" % name] if frame.shape[1] == 0 else []


# ------------------------------------------------------------------ expectations
def expectation_problems(
    expect: dict[str, Any], results: list[Result], seconds: float, progress_events: int
) -> list[str]:
    problems: list[str] = []
    by_name = {r["name"]: r for r in results}
    for name, wanted in expect.get("results", {}).items():
        result = by_name.get(name)
        if result is None:
            problems.append("no result named %r" % name)
            continue
        problems += _compare(name, result, wanted)
    if "max_seconds" in expect and seconds > expect["max_seconds"]:
        problems.append("took %.1f s, limit %s s" % (seconds, expect["max_seconds"]))
    if progress_events < expect.get("progress_events_min", 0):
        problems.append(
            "%d progress updates, expected at least %d" % (progress_events, expect["progress_events_min"])
        )
    return problems


def _compare(name: str, result: Result, wanted: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    kind = result["type"]
    if kind in RESULT_KEYS:  # an unknown key would be an assertion that silently never runs
        for key in sorted(set(wanted) - RESULT_KEYS[kind]):
            problems.append(
                "%s: unknown expectation %r for a %s result (allowed: %s)"
                % (name, key, kind, ", ".join(sorted(RESULT_KEYS[kind])) or "none")
            )
        if problems:
            return problems
    if kind in ("image", "labels"):
        import tifffile

        array = tifffile.imread(result["path"])
        if "shape" in wanted and list(array.shape) != list(wanted["shape"]):
            problems.append("%s: shape %s, expected %s" % (name, list(array.shape), wanted["shape"]))
        if "dtype" in wanted and str(array.dtype) != wanted["dtype"]:
            problems.append("%s: dtype %s, expected %s" % (name, array.dtype, wanted["dtype"]))
        if "mean" in wanted and not _close(float(array.mean()), wanted["mean"]):
            problems.append("%s: mean %.6g, expected %s" % (name, array.mean(), wanted["mean"]))
        if "max" in wanted and not _close(float(array.max()), wanted["max"]):
            problems.append("%s: max %.6g, expected %s" % (name, array.max(), wanted["max"]))
        if "n_labels" in wanted:
            import numpy as np

            n = int(len(np.unique(array)) - (1 if (array == 0).any() else 0))
            if n != wanted["n_labels"]:
                problems.append("%s: %d labels, expected %d" % (name, n, wanted["n_labels"]))
    elif kind == "table":
        import pandas as pd

        frame = pd.read_csv(result["path"])
        if "columns" in wanted and not set(wanted["columns"]) <= set(frame.columns):
            problems.append(
                "%s: missing columns %s" % (name, sorted(set(wanted["columns"]) - set(frame.columns)))
            )
        if "rows" in wanted and len(frame) != wanted["rows"]:
            problems.append("%s: %d rows, expected %d" % (name, len(frame), wanted["rows"]))
        for key, value in wanted.get("cells", {}).items():  # "column[row]": value
            column, _, row = key.partition("[")
            try:
                actual = frame[column].iloc[int(row.rstrip("]"))]
            except (KeyError, ValueError, IndexError):
                problems.append("%s: no cell %s" % (name, key))
                continue
            if not _close(actual, value):
                problems.append("%s: %s is %r, expected %r" % (name, key, actual, value))
    elif kind == "values":
        for key, value in wanted.get("equals", wanted).items():
            actual = result["values"].get(key)
            if isinstance(value, dict) and "approx" in value:  # {"approx": 12.0, "tol": 0.5}
                ok = isinstance(actual, (int, float)) and abs(actual - value["approx"]) <= value.get(
                    "tol", 1e-6
                )
            else:
                ok = key in result["values"] and _close(actual, value)
            if not ok:
                problems.append("%s: %s is %r, expected %r" % (name, key, actual, value))
    elif kind == "message" and "contains" in wanted:
        if wanted["contains"] not in result["text"]:
            problems.append("%s: the message lacks %r" % (name, wanted["contains"]))
    elif kind == "points":
        import pandas as pd

        frame = pd.read_csv(result["path"])
        if "rows" in wanted and len(frame) != wanted["rows"]:
            problems.append("%s: %d points, expected %d" % (name, len(frame), wanted["rows"]))
        if "columns" in wanted and not set(wanted["columns"]) <= set(frame.columns):
            problems.append("%s: missing columns %s" % (name, sorted(set(wanted["columns"]) - set(frame.columns))))
    elif kind == "affine" and "matrix" in wanted:
        expected = wanted["matrix"]
        if not (
            isinstance(expected, list)
            and len(expected) == 3
            and all(isinstance(row, list) and len(row) == 3 for row in expected)
        ):
            return ["%s: the expected matrix must be 3x3 (a list of three rows of three numbers)" % name]
        flat = [v for row in result["matrix_yx"] for v in row]
        if len(flat) != 9 or not all(
            _close(a, b) for a, b in zip(flat, [v for row in expected for v in row])
        ):
            problems.append("%s: matrix %s, expected %s" % (name, result["matrix_yx"], expected))
    return problems


def _close(actual: Any, wanted: Any, tolerance: float = 1e-6) -> bool:
    if isinstance(wanted, (int, float)) and not isinstance(wanted, bool) and isinstance(actual, (int, float)):
        return abs(actual - wanted) <= tolerance * max(1.0, abs(wanted))
    return actual == wanted


# ------------------------------------------------------------------ running
def run_case(
    case: CaseSpec,
    tools_by_id: dict[str, ToolSchema],
    worker_args: dict[str, Any],
    timeout: float,
    check_cancel: bool,
) -> CaseReport:
    """Returns {tool, status, seconds, problems, warnings, skipped}."""
    report: CaseReport = {
        "tool": case["tool"],
        "problems": [],
        "warnings": [],
        "skipped": None,
        "seconds": 0.0,
    }
    if case.get("skip"):
        report["status"], report["skipped"] = "SKIPPED", case["skip"]
        return report
    tool = tools_by_id.get(case["tool"])
    if tool is None:
        report["status"] = "ERROR"
        report["problems"] = ["no such tool; declared: %s" % ", ".join(sorted(tools_by_id))]
        return report
    expect = case.get("expect", {})
    updates: list[tuple[str, float | None]] = []
    with tempfile.TemporaryDirectory(prefix="lc_test_") as scratch:
        inputs = dict(_resolve_paths(case, tool), _job_dir=str(Path(scratch) / "job"))
        started = time.time()
        with client.WorkerProcess(**worker_args) as worker:
            task = worker.task(tool["id"], inputs, lambda m, f: updates.append((m, f)))
            if case.get("cancel_after_s") is not None:
                time.sleep(case["cancel_after_s"])
                task.cancel()
                task.wait(CANCEL_GRACE_S)
            else:
                task.wait(timeout)
            if not task.done.is_set():
                worker.kill()
                report["problems"].append(
                    "did not finish within %s s"
                    % (CANCEL_GRACE_S if case.get("cancel_after_s") is not None else timeout)
                )
                task.status = "TIMEOUT"
            stderr = "".join(worker.stderr)
        report["seconds"] = round(time.time() - started, 2)
        report["status"] = task.status
        want = expect.get("status", "CANCELED" if case.get("cancel_after_s") is not None else "COMPLETE")
        if task.status != want and task.status != "TIMEOUT":
            detail = (task.error or "").strip()
            report["problems"].append(
                "status %s, expected %s%s" % (task.status, want, ": " + detail if detail else "")
            )
            if task.traceback:
                report["traceback"] = task.traceback
        elif task.status == "COMPLETE":
            results = task.outputs.get("results", [])
            report["problems"] += contract_problems(tool, results)
            report["problems"] += expectation_problems(expect, results, report["seconds"], len(updates))
        else:
            if "code" in expect and task.code != expect["code"]:
                report["problems"].append("error code %r, expected %r" % (task.code, expect["code"]))
            if "message_contains" in expect and expect["message_contains"] not in (task.error or ""):
                report["problems"].append(
                    "error message %r lacks %r" % (task.error, expect["message_contains"])
                )
        if stderr.strip() and task.status != "COMPLETE" and task.status != want:
            report["stderr_tail"] = stderr.strip().splitlines()[-5:]
    if check_cancel and case.get("cancel_after_s") is None:
        cancel_problems, cancel_warnings = _cancel_check(tool, case, worker_args)
        report[
            "problems"
        ] += cancel_problems  # --check-cancel asked for a verdict: ignoring a cancel request is a failure
        report["warnings"] += cancel_warnings
    return report


def _cancel_check(
    tool: ToolSchema, case: CaseSpec, worker_args: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Start the tool again, cancel it right away: a tool that never calls check_cancel() will run to the end.
    -> (problems, warnings)"""
    with (
        tempfile.TemporaryDirectory(prefix="lc_cancel_") as scratch,
        client.WorkerProcess(**worker_args) as worker,
    ):
        inputs = dict(_resolve_paths(case, tool), _job_dir=str(Path(scratch) / "job"))
        task = worker.task(tool["id"], inputs)
        task.launched.wait(60)
        time.sleep(
            1.0
        )  # let the tool really start: a cancel that arrives first is honoured without the tool's help
        if task.done.is_set():
            return [], []  # too quick to cancel: nothing to learn
        task.cancel(grace=None)  # this check does its own timing
        task.wait(CANCEL_GRACE_S)
        if not task.done.is_set():
            worker.kill()
            return [
                "ignored a cancel request for %d s: call check_cancel() inside the main loop" % CANCEL_GRACE_S
            ], []
        if task.status == "COMPLETE":
            return [], ["completed despite a cancel request (no check_cancel() call reached in time)"]
    return [], []


def run_suite(
    module: str,
    pythonpath: Sequence[str | Path],
    cases: list[CaseSpec] | None,
    only: str | None = None,
    samples: dict[str, str] | None = None,
    timeout: float = 120,
    check_cancel: bool = False,
    python: str | None = None,
) -> tuple[list[CaseReport], list[str]]:
    """Returns (reports, tools that no case covers)."""
    for path in pythonpath:
        sys.path.insert(0, str(path))
    importlib.import_module(module)
    from .introspection import describe_tools

    schema = describe_tools(module)
    tools_by_id = {t["id"]: t for t in schema["tools"]}
    if cases is None:
        cases = smoke_cases(schema, samples or {})
    if only:
        cases = [c for c in cases if c["tool"] == only]
    worker_args = {"module": module, "pythonpath": list(pythonpath), "python": python}
    reports = [run_case(c, tools_by_id, worker_args, timeout, check_cancel) for c in cases]
    untested = sorted(set(tools_by_id) - {c["tool"] for c in cases})
    return reports, untested


def format_report(reports: list[CaseReport], untested: list[str]) -> str:
    lines = []
    for r in reports:
        mark = "-" if r["status"] == "SKIPPED" else ("✖" if r["problems"] else "✔")
        lines.append("%s %-22s %-9s %5.1f s" % (mark, r["tool"], r["status"], r["seconds"]))
        if r["skipped"]:
            lines.append("      skipped: %s" % r["skipped"])
        for text in r["problems"]:
            lines.append("      ✖ %s" % text)
        for text in r["warnings"]:
            lines.append("      ⚠ %s" % text)
        for text in r.get("stderr_tail", []):
            lines.append("      | %s" % text)
    if untested:
        lines.append("⚠ tools with no test case: %s" % ", ".join(untested))
    failed = sum(1 for r in reports if r["problems"])
    ran = sum(1 for r in reports if r["status"] != "SKIPPED")
    lines.append("%d run, %d failed, %d skipped" % (ran, failed, len(reports) - ran))
    return "\n".join(lines)


__all__ = ["run_suite", "format_report", "load_cases", "smoke_cases", "validate_case"]
