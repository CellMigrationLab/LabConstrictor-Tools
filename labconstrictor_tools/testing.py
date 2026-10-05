"""`labconstrictor-tools test`: run tools through the real worker on small samples and check the outcome.

Two layers of checks:
* contract checks, automatic for every run that completes: the results match the declared outputs, files exist
  and open, images use a dtype every host can read, tables parse, affines are finite 3x3, values are JSON;
* expectations, optional, written by the author in a cases file (see docs/AUTHORING.md).
"""

import importlib
import json
import math
import sys
import tempfile
import time
from pathlib import Path

from . import client

FIJI_SAFE_DTYPES = ("uint8", "uint16", "int16", "float32")
CANCEL_GRACE_S = 10


# ------------------------------------------------------------------ cases
def smoke_cases(schema, samples):
    """One case per tool: defaults for optional parameters, `samples` (name=path) for required files/images."""
    cases = []
    for tool in schema["tools"]:
        inputs, skip = {}, None
        for param in tool["inputs"]:
            if param["name"] in samples:
                inputs[param["name"]] = samples[param["name"]]
            elif param["required"]:
                skip = "required parameter %r has no --sample" % param["name"]
        cases.append({"tool": tool["id"], "inputs": inputs, "skip": skip})
    return cases


def load_cases(path):
    path = Path(path).resolve()
    cases = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", [])
    for case in cases:  # relative file names are relative to the cases file
        for name, value in list(case.get("inputs", {}).items()):
            if isinstance(value, str) and (path.parent / value).exists():
                case["inputs"][name] = str((path.parent / value).resolve())
    return cases


# ------------------------------------------------------------------ contract checks
def contract_problems(tool, results):
    problems = []
    declared = [(o["name"], o["type"]) for o in tool["outputs"]]
    got = [(r.get("name"), r.get("type")) for r in results]
    if declared != got:
        problems.append("results %s do not match declared outputs %s" % (got, declared))
        return problems
    for result in results:
        problems += _result_problems(result)
    return problems


def _result_problems(result):
    kind, name = result["type"], result["name"]
    if kind in ("image", "labels"):
        return _image_problems(name, result)
    if kind == "table":
        return _table_problems(name, result)
    if kind == "file":
        return (
            [] if Path(result["path"]).exists() else ["%s: file %s does not exist" % (name, result["path"])]
        )
    if kind == "values":
        try:
            json.dumps(result["values"], allow_nan=False)
        except (TypeError, ValueError) as error:
            return ["%s: values are not plain JSON (%s)" % (name, error)]
    if kind == "affine":
        matrix = result.get("matrix_yx")
        ok = (
            isinstance(matrix, list)
            and len(matrix) == 3
            and all(len(row) == 3 and all(math.isfinite(v) for v in row) for row in matrix)
        )
        return [] if ok else ["%s: affine is not a finite 3x3 matrix" % name]
    return []


def _image_problems(name, result):
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


def _table_problems(name, result):
    import pandas as pd

    try:
        frame = pd.read_csv(result["path"])
    except Exception as error:  # noqa: BLE001 - any parse failure is a finding
        return ["%s: table does not parse (%s)" % (name, error)]
    return ["%s: table has no columns" % name] if frame.shape[1] == 0 else []


# ------------------------------------------------------------------ expectations
def expectation_problems(expect, results, seconds, progress_events):
    problems = []
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


def _compare(name, result, wanted):
    problems = []
    kind = result["type"]
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
            if key not in result["values"] or not _close(result["values"][key], value):
                problems.append("%s: %s is %r, expected %r" % (name, key, result["values"].get(key), value))
    elif kind == "affine" and "matrix" in wanted:
        flat = [v for row in result["matrix_yx"] for v in row]
        if not all(_close(a, b) for a, b in zip(flat, [v for row in wanted["matrix"] for v in row])):
            problems.append("%s: matrix %s, expected %s" % (name, result["matrix_yx"], wanted["matrix"]))
    return problems


def _close(actual, wanted, tolerance=1e-6):
    if isinstance(wanted, (int, float)) and not isinstance(wanted, bool) and isinstance(actual, (int, float)):
        return abs(actual - wanted) <= tolerance * max(1.0, abs(wanted))
    return actual == wanted


# ------------------------------------------------------------------ running
def run_case(case, tools_by_id, worker_args, timeout, check_cancel):
    """Returns {tool, status, seconds, problems, warnings, skipped}."""
    report = {"tool": case["tool"], "problems": [], "warnings": [], "skipped": None, "seconds": 0.0}
    if case.get("skip"):
        report.update(status="SKIPPED", skipped=case["skip"])
        return report
    tool = tools_by_id.get(case["tool"])
    if tool is None:
        report.update(
            status="ERROR", problems=["no such tool; declared: %s" % ", ".join(sorted(tools_by_id))]
        )
        return report
    expect = case.get("expect", {})
    updates = []
    with tempfile.TemporaryDirectory(prefix="lc_test_") as scratch:
        inputs = dict(case.get("inputs", {}), _job_dir=str(Path(scratch) / "job"))
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
        report["warnings"] += _cancel_warnings(tool, case, worker_args)
    return report


def _cancel_warnings(tool, case, worker_args):
    """Start the tool again, cancel it right away: a tool that never calls check_cancel() will run to the end."""
    with client.WorkerProcess(**worker_args) as worker:
        inputs = dict(case.get("inputs", {}))
        task = worker.task(tool["id"], inputs)
        time.sleep(0.2)
        if task.done.is_set():
            return []  # too quick to cancel: nothing to learn
        task.cancel()
        task.wait(CANCEL_GRACE_S)
        if not task.done.is_set():
            worker.kill()
            return [
                "ignored a cancel request for %d s: call check_cancel() inside the main loop" % CANCEL_GRACE_S
            ]
        if task.status == "COMPLETE":
            return ["completed despite a cancel request (no check_cancel() call reached in time)"]
    return []


def run_suite(
    module, pythonpath, cases, only=None, samples=None, timeout=120, check_cancel=False, python=None
):
    """Returns (reports, problems_found:bool)."""
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


def format_report(reports, untested):
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


__all__ = ["run_suite", "format_report", "load_cases", "smoke_cases"]
