"""Runs a round-trip `Case` through one real transport and compares what comes back with the case's oracle.

Transports (every one is the production entry point a person or a host uses):
  worker    `client.WorkerProcess`: the worker protocol over a real subprocess (what Napari and other Python hosts do)
  cli       `python -m labconstrictor_tools run APP TOOL name=value ...` in a subprocess
  snippet   the Python text of `command.python_snippet`, executed with `python -c`
  terminal  the line of `command.command_line`, executed through the shell of this machine (POSIX) or as one command line
  notebook  `notebook.ToolForm`: the controls are set and `run()` is called, in this process

Nothing here converts values for the tool: the harness only writes what a host would write (TIFF, CSV, files), reads
what a host would read, and compares with the expectations of roundtrip_cases.py, which are computed independently.
"""

from __future__ import annotations

import ast
import contextlib
import csv
import hashlib
import io
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from multiprocessing import resource_tracker, shared_memory
from pathlib import Path
from typing import Any

import _paths
import numpy as np
import roundtrip_app
import tifffile
from roundtrip_cases import (
    APP_MODULE,
    Case,
    Expect,
    FileSpec,
    FolderSpec,
    JsonFile,
    MissingPath,
    OutAffine,
    OutFile,
    OutImage,
    OutOutlines,
    OutPoints,
    OutShapes,
    OutTable,
    OutText,
    SentPath,
    Shm,
)

from labconstrictor_tools import command
from labconstrictor_tools.client import WorkerProcess

APP = "roundtrip"
TASK_TIMEOUT_S = 120
SUBPROCESS_TIMEOUT_S = 180
TOOLERROR_CODE = re.compile(r"^[a-z][a-z0-9_]*$")  # ToolError codes; a Python exception class is CamelCase
TRANSPORTS = ("worker", "cli", "snippet", "terminal", "notebook")


# ------------------------------------------------------------------------------------------- what came back
@dataclass
class Observed:
    status: str  # COMPLETE | FAILED | other (CRASHED, CANCELED, RUNNING, ...)
    results: list[dict[str, Any]] = field(default_factory=list)
    code: str | None = None
    error: str | None = None
    job_dir: str | None = None


# ------------------------------------------------------------------------------------------------ session
class Session:
    """Shared state of a test run: a private folder, a registered copy of the example app, one reusable worker."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="lc_roundtrip_"))
        self._worker: WorkerProcess | None = None
        self._registered = False
        self._shm: list[shared_memory.SharedMemory] = []
        self._count = 0
        self._lock = threading.Lock()
        self.tools = roundtrip_app.schemas(APP_MODULE)

    # ---- lifecycle
    def close(self) -> None:
        if self._worker is not None:
            self._worker.close()
        for block in self._shm:
            _release(block)
        shutil.rmtree(self.root, ignore_errors=True)

    def case_dir(self) -> Path:
        with self._lock:
            self._count += 1
            folder = self.root / ("c%d" % self._count)
        folder.mkdir()
        return folder

    def worker(self) -> WorkerProcess:
        if self._worker is None or not self._worker.alive:
            self._worker = start_worker(quiet_resource_tracker=True)
        return self._worker

    def register_app(self) -> None:
        """Register the example app in the private LC_HOME, as an installer would (the CLI and the copied text need it)."""
        if self._registered:
            return
        env = {**os.environ, "PYTHONPATH": str(_paths.ROOT)}
        done = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "register", "--name", APP, "--prefix", str(_paths.GENERIC_PREFIX),
             "--module", APP_MODULE, "--version", "0"],
            capture_output=True, text=True, env=env, timeout=SUBPROCESS_TIMEOUT_S, encoding="utf-8",
        )  # fmt: skip
        if done.returncode:
            raise RuntimeError("cannot register the example app: %s" % done.stderr[-2000:])
        self._registered = True

    def subprocess_env(self) -> dict[str, str]:
        return {
            **os.environ,
            "PYTHONPATH": str(_paths.ROOT),
            "LC_APPS_PATH": "",
            "PYTHONIOENCODING": "utf-8",
            "MPLBACKEND": "Agg",
        }

    # ---- host -> wire
    def materialise(self, case: Case, folder: Path) -> tuple[dict[str, Any], dict[str, str]]:
        """What a host sends for the case's values: (wire inputs, {parameter: path text of the files it wrote})."""
        wire: dict[str, Any] = {}
        sent: dict[str, str] = {}
        for name, value in case.send.items():
            wire[name], path = self._to_wire(name, value, folder)
            if path is not None:
                sent[name] = path
        return wire, sent

    def _to_wire(self, name: str, value: Any, folder: Path) -> tuple[Any, str | None]:
        if isinstance(value, Shm):
            return self._share(value.array), None
        if isinstance(value, np.ndarray):
            path = folder / (name + ".tif")
            tifffile.imwrite(
                path, value, photometric="minisblack"
            )  # a stack is pages, never "RGB planes" (as Fiji writes it)
            return str(path), str(path)
        if hasattr(value, "to_csv"):
            path = folder / (name + ".csv")
            write_csv(value, path)
            return str(path), str(path)
        if isinstance(value, FileSpec):
            path = folder / value.name
            path.write_bytes(value.data)
            return str(path), str(path)
        if isinstance(value, FolderSpec):
            path = folder / value.name
            path.mkdir()
            for entry, data in value.entries:
                (path / entry).write_bytes(data)
            return str(path), str(path)
        if isinstance(value, JsonFile):
            path = folder / value.name
            path.write_text(
                json.dumps(value.payload), encoding="utf-8"
            )  # NaN and Infinity are written as Python does
            return str(path), str(path)
        if isinstance(value, MissingPath):
            path = folder / value.name
            return str(path), str(path)
        return value, None

    def _share(self, array: np.ndarray) -> dict[str, Any]:
        data = np.ascontiguousarray(array)
        block = shared_memory.SharedMemory(create=True, size=max(data.nbytes, 1))
        self._shm.append(block)
        np.ndarray(data.shape, dtype=data.dtype, buffer=block.buf)[...] = data
        return {
            "appose_type": "ndarray",
            "shm": {"name": block.name, "size": block.size},
            "shape": list(data.shape),
            "dtype": str(data.dtype),
        }


def start_worker(quiet_resource_tracker: bool = False) -> WorkerProcess:
    """A worker of the example app started as a host does (module mode). Shared-memory cases make Python's resource tracker
    complain on the worker's stderr when it exits (see test_roundtrip_shared_memory.py); a matrix run does not need to see that.
    """
    old = os.environ.get("PYTHONWARNINGS")
    if quiet_resource_tracker:
        os.environ["PYTHONWARNINGS"] = "ignore:resource_tracker"
    try:
        return WorkerProcess(module=APP_MODULE, pythonpath=[str(_paths.ROOT)])
    finally:
        if old is None:
            os.environ.pop("PYTHONWARNINGS", None)
        else:
            os.environ["PYTHONWARNINGS"] = old


def write_csv(frame: Any, path: Path) -> None:
    """A table as a host writes it: UTF-8, header, every number by its exact text (repr), empty for NaN, True/False."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([str(c) for c in frame.columns])
        for row in frame.itertuples(index=False):
            writer.writerow([_csv_text(v) for v in row])


def _csv_text(value: Any) -> str:
    value = value.item() if hasattr(value, "item") else value
    if isinstance(value, float):
        return "" if math.isnan(value) else repr(value)
    return str(value)


def _release(block: shared_memory.SharedMemory) -> None:
    try:
        block.close()
    except BufferError:
        pass  # a view is still alive; the mapping goes with the process
    try:
        block.unlink()
    except FileNotFoundError:
        # the worker's resource tracker already removed it (F13): tell ours, or it complains about a "leak" at exit
        resource_tracker.unregister(block._name, "shared_memory")  # type: ignore[attr-defined]


# ------------------------------------------------------------------------------------------------ transports
def run_worker(session: Session, case: Case, wire: dict[str, Any], folder: Path) -> Observed:
    worker = session.worker()
    task = worker.task(case.tool, {**wire, "_job_dir": str(folder / "out")})
    task.wait(TASK_TIMEOUT_S)
    if not task.done.is_set():
        worker.kill()
        return Observed("TIMEOUT", error="no answer after %s s" % TASK_TIMEOUT_S)
    if task.status == "CRASHED":
        worker.kill()  # the next case gets a fresh worker
    return Observed(
        task.status, task.outputs.get("results", []), task.code, task.error, task.outputs.get("job_dir")
    )


def cli_arguments(tool: dict[str, Any], values: dict[str, Any]) -> list[str]:
    """`name=value` words as a person types them: booleans in lower case, floats with repr, unset parameters left out."""
    words = []
    kinds = {p["name"]: p["type"] for p in tool["inputs"]}
    for name, value in values.items():
        if value is None:
            continue
        if isinstance(value, bool):
            text = "true" if value else "false"
        elif isinstance(value, float):
            text = repr(value)
        else:
            text = str(value)
        assert name in kinds, name
        words.append("%s=%s" % (name, text))
    return words


def _parse_cli_report(stdout: str) -> dict[str, Any]:
    start = stdout.index("{")
    report, _ = json.JSONDecoder().raw_decode(stdout[start:])
    return report


def _observed_from_report(report: dict[str, Any]) -> Observed:
    return Observed(
        report["status"],
        report.get("results", []),
        report.get("code"),
        report.get("error"),
        report.get("job_dir"),
    )


def run_cli(session: Session, case: Case, wire: dict[str, Any], folder: Path) -> Observed:
    session.register_app()
    command_words = [sys.executable, "-m", "labconstrictor_tools", "run", APP, case.tool]
    command_words += cli_arguments(session.tools[case.tool], wire)
    command_words += ["--out", str(folder / "out"), "--no-record", "--timeout", str(TASK_TIMEOUT_S)]
    done = subprocess.run(
        command_words, capture_output=True, env=session.subprocess_env(), timeout=SUBPROCESS_TIMEOUT_S
    )
    stdout = done.stdout.decode("utf-8", errors="replace")
    if "{" not in stdout:
        return Observed("NO_REPORT", error=(done.stderr.decode("utf-8", errors="replace") + stdout)[-2000:])
    return _observed_from_report(_parse_cli_report(stdout))


def run_snippet(session: Session, case: Case, wire: dict[str, Any], folder: Path) -> Observed:
    session.register_app()
    text = command.python_snippet(APP, session.tools[case.tool], wire)
    done = subprocess.run(
        [sys.executable, "-c", text],
        capture_output=True,
        env=session.subprocess_env(),
        timeout=SUBPROCESS_TIMEOUT_S,
    )
    stdout = done.stdout.decode("utf-8", errors="replace").strip()
    status, _, rest = stdout.partition(" ")
    if status == "COMPLETE":
        outputs = ast.literal_eval(rest)
        return Observed("COMPLETE", outputs["results"], job_dir=outputs.get("job_dir"))
    code = re.match(r"\[([^\]]+)\]", rest)
    return Observed(
        status or "NO_REPORT",
        code=code.group(1) if code else None,
        error=rest or done.stderr.decode("utf-8", errors="replace")[-2000:],
    )


def run_terminal(session: Session, case: Case, wire: dict[str, Any], folder: Path) -> Observed:
    session.register_app()
    line = command.command_line(APP, session.tools[case.tool], wire, python=sys.executable)
    assert not line.startswith("#"), "a case must not need a placeholder file"
    # a real shell on POSIX; on Windows the line is one command line for the process (cmd.exe is not involved)
    done = subprocess.run(
        line,
        shell=(os.name != "nt"),
        capture_output=True,
        env=session.subprocess_env(),
        timeout=SUBPROCESS_TIMEOUT_S,
    )
    stdout = done.stdout.decode("utf-8", errors="replace")
    if "{" not in stdout:
        return Observed("NO_REPORT", error=(done.stderr.decode("utf-8", errors="replace") + stdout)[-2000:])
    return _observed_from_report(_parse_cli_report(stdout))


def run_notebook(session: Session, case: Case, wire: dict[str, Any], folder: Path) -> Observed:
    from labconstrictor_tools.notebook import ToolForm

    module = sys.modules[APP_MODULE]
    form = ToolForm(getattr(module, case.tool))
    for name, value in wire.items():
        form.controls[name].value = value
    old = tempfile.tempdir
    tempfile.tempdir = str(
        folder
    )  # the form writes its results to a fresh temporary folder: keep it inside the case folder
    try:
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):  # the form prints results
            logging.disable(logging.CRITICAL)  # ... and logs the traceback of every failure it shows
            results = form.run()
    finally:
        logging.disable(logging.NOTSET)
        tempfile.tempdir = old
    if results is not None:
        return Observed("COMPLETE", results)
    found = re.search(r"<b>([^<]*)</b>: (.*)", form.status.value, re.S)
    return Observed("FAILED", code=found.group(1) if found else None, error=form.status.value)


RUNNERS = {
    "worker": run_worker,
    "cli": run_cli,
    "snippet": run_snippet,
    "terminal": run_terminal,
    "notebook": run_notebook,
}


# ------------------------------------------------------------------------------------------------ comparison
def same(got: Any, want: Any) -> bool:
    """Equal in value AND type (3 is not 3.0 is not "3"; True is not 1; -0.0 is not 0.0)."""
    if isinstance(want, bool) or isinstance(got, bool):
        return type(got) is type(want) and got == want
    if isinstance(want, float):
        return isinstance(got, float) and got == want and math.copysign(1.0, got) == math.copysign(1.0, want)
    if isinstance(want, int):
        return type(got) is int and got == want
    if isinstance(want, str):
        return type(got) is str and got == want
    if want is None:
        return got is None
    if isinstance(want, (list, tuple)):
        return isinstance(got, list) and len(got) == len(want) and all(same(g, w) for g, w in zip(got, want))
    if isinstance(want, dict):
        return (
            isinstance(got, dict) and sorted(got) == sorted(want) and all(same(got[k], want[k]) for k in want)
        )
    return bool(got == want)


def non_finite_floats(node: Any, where: str = "results") -> list[str]:
    """Places where a NaN or infinity travelled as a number: strict JSON has none (they are sent as null)."""
    if isinstance(node, float) and not math.isfinite(node):
        return [where]
    if isinstance(node, dict):
        return [p for k, v in node.items() for p in non_finite_floats(v, "%s.%s" % (where, k))]
    if isinstance(node, (list, tuple)):
        return [p for i, v in enumerate(node) for p in non_finite_floats(v, "%s[%d]" % (where, i))]
    return []


def _resolve_sent(expected: Any, sent: dict[str, str]) -> Any:
    if isinstance(expected, SentPath):
        return sent[expected.param]
    if isinstance(expected, dict):
        return {k: _resolve_sent(v, sent) for k, v in expected.items()}
    return expected


def check(session: Session, case: Case, got: Observed, sent: dict[str, str]) -> list[str]:
    """Every difference between what came back and the oracle, as readable sentences (empty = the round trip held)."""
    want = case.expect
    if want.status != got.status:
        return [
            "status %s, expected %s (code %s: %s)"
            % (got.status, want.status, got.code, (got.error or "")[:300])
        ]
    if want.status == "FAILED":
        return _check_failure(want, got)
    return _check_success(session, case, got, sent)


def _check_failure(want: Expect, got: Observed) -> list[str]:
    problems = []
    if want.code is not None and got.code != want.code:
        problems.append("failure code %r, expected %r (%s)" % (got.code, want.code, (got.error or "")[:300]))
    if want.toolerror and not (got.code and TOOLERROR_CODE.match(got.code)):
        problems.append(
            "failure code %r is not a ToolError code: a Python exception reached the person (%s)"
            % (got.code, (got.error or "")[:200])
        )
    if want.message is not None and want.message not in (got.error or ""):
        problems.append("message %r does not mention %r" % ((got.error or "")[:300], want.message))
    if not got.error or not got.error.strip():
        problems.append("a failure without a message")
    return problems


def _check_success(session: Session, case: Case, got: Observed, sent: dict[str, str]) -> list[str]:
    problems = non_finite_floats(got.results)
    problems = ["NaN/Infinity as a JSON number at %s" % p for p in problems]
    declared = [(o["name"], o["type"]) for o in session.tools[case.tool]["outputs"]]
    seen = [(r.get("name"), r.get("type")) for r in got.results]
    if declared != seen:
        return problems + ["results %s are not the declared outputs %s" % (seen, declared)]
    by_name = {r["name"]: r for r in got.results}
    want = case.expect
    if want.received is not None:
        values = (by_name.get("received") or by_name.get("values") or {}).get("values")
        if values is None:
            problems.append("no values result to compare")
        else:
            for key, expected in _resolve_sent(want.received, sent).items():
                if key not in values:
                    problems.append("the report has no %r (has %s)" % (key, sorted(values)))
                elif not same(values[key], expected):
                    problems.append(
                        "received %s = %r, expected %r" % (key, _short(values[key]), _short(expected))
                    )
    for name, out in want.outputs.items():
        problems += ["output %s: %s" % (name, p) for p in _check_output(out, by_name[name], sent)]
    return problems


def _short(value: Any, limit: int = 160) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + "...(%d chars)" % len(text)


def _check_output(out: Any, result: dict[str, Any], sent: dict[str, str]) -> list[str]:
    if isinstance(out, OutImage):
        return _check_image(out, result)
    if isinstance(out, OutTable):
        return _check_table(out, result)
    if isinstance(out, OutPoints):
        return _check_points(out, result)
    if isinstance(out, OutText):
        return (
            []
            if result.get("text") == out.text
            else ["text %r, expected %r" % (_short(result.get("text")), _short(out.text))]
        )
    if isinstance(out, OutFile):
        return _check_file(out, result, sent)
    if isinstance(out, OutShapes):
        return _check_shapes(out, result)
    if isinstance(out, OutOutlines):
        return _check_outlines(out, result)
    if isinstance(out, OutAffine):
        return _check_affine(out, result)
    return ["no comparator for %r" % type(out).__name__]


def _check_image(out: OutImage, result: dict[str, Any]) -> list[str]:
    got = tifffile.imread(result["path"])
    problems = []
    if str(got.dtype) not in out.dtypes:
        problems.append("dtype %s, expected one of %s" % (got.dtype, out.dtypes))
    if tuple(got.shape) != tuple(out.values.shape):
        return problems + ["shape %s, expected %s" % (got.shape, out.values.shape)]
    if len(result.get("axes", "")) != got.ndim:
        problems.append("axes %r do not describe %d dimensions" % (result.get("axes"), got.ndim))
    want = np.asarray(out.values)
    if want.dtype.kind == "f" or got.dtype.kind == "f":
        equal = np.array_equal(got.astype(np.float64), want.astype(np.float64), equal_nan=True)
        if equal and want.dtype.kind == "f":
            equal = bool(
                np.array_equal(np.signbit(got.astype(np.float64)), np.signbit(want.astype(np.float64)))
            )
    else:
        equal = np.array_equal(
            got.astype(np.int64) if got.dtype.itemsize < 8 else got,
            want.astype(np.int64) if want.dtype.itemsize < 8 else want,
        )
    if not equal:
        different = int(np.count_nonzero(got.astype(np.float64) != want.astype(np.float64)))
        problems.append(
            "values differ (about %d of %d pixels, first got %s, want %s)"
            % (different, want.size, got.ravel()[:4].tolist(), want.ravel()[:4].tolist())
        )
    return problems


def _read_rows(path: str) -> list[list[str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def _cell_problem(text: str, want: Any, where: str) -> str | None:
    """Does the text of a CSV cell mean `want`? (a host reads CSV text: numbers by their text, NaN as empty)"""
    if want is None:
        return None if text == "" else "%s: %r, expected an empty cell" % (where, text)
    if isinstance(want, bool):
        return None if text == str(want) else "%s: %r, expected %s" % (where, text, want)
    if isinstance(want, int):
        return None if text == str(want) else "%s: %r, expected the integer %d" % (where, text, want)
    if isinstance(want, float):
        try:
            value = float(text)
        except ValueError:
            return "%s: %r is not a number, expected %r" % (where, text, want)
        ok = value == want and math.copysign(1.0, value) == math.copysign(1.0, want)
        return None if ok else "%s: %r, expected %r" % (where, text, want)
    return None if text == want else "%s: %r, expected %r" % (where, _short(text), _short(want))


def _check_cells(
    columns: list[str], data: dict[str, list[Any]], path: str, as_float: tuple[int, ...] = ()
) -> list[str]:
    rows = _read_rows(path)
    if not rows:
        return ["the CSV is empty (not even a header)"]
    problems = []
    if rows[0] != columns:
        return ["columns %s, expected %s" % (rows[0], columns)]
    n_rows = len(data["0"]) if data else 0
    if len(rows) - 1 != n_rows:
        return ["%d rows, expected %d" % (len(rows) - 1, n_rows)]
    for i in range(len(columns)):
        for j, want in enumerate(data[str(i)]):
            text = rows[j + 1][i]
            problem = _cell_problem(
                text,
                float(want) if (i in as_float and want is not None) else want,
                "column %r row %d" % (columns[i], j),
            )
            if problem:
                problems.append(problem)
                if len(problems) >= 5:
                    return problems
    return problems


def _check_table(out: OutTable, result: dict[str, Any]) -> list[str]:
    return _check_cells(out.columns, out.columns_data, result["path"])


def _check_points(out: OutPoints, result: dict[str, Any]) -> list[str]:
    problems = []
    if result.get("columns") != out.columns:
        problems.append("columns %s, expected %s" % (result.get("columns"), out.columns))
    n = len(out.columns_data["0"]) if out.columns_data else 0
    if result.get("n") != n:
        problems.append("n = %r, expected %d" % (result.get("n"), n))
    return problems + _check_cells(out.columns, out.columns_data, result["path"], as_float=(0, 1))


def _check_file(out: OutFile, result: dict[str, Any], sent: dict[str, str]) -> list[str]:
    problems = []
    path = Path(result["path"])
    if out.same_path_as and result["path"] != sent[out.same_path_as]:
        problems.append(
            "path %r, expected the path that was sent %r" % (result["path"], sent[out.same_path_as])
        )
    if out.digest is not None:
        if not path.is_file():
            problems.append("the result file %s does not exist" % path)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != out.digest:
            problems.append("the result file's content differs from the file that was sent")
    return problems


def _check_shapes(out: OutShapes, result: dict[str, Any]) -> list[str]:
    problems = []
    collection = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    expected = json.loads(json.dumps(out.collection))
    if result.get("n") != len(expected["features"]):
        problems.append("n = %r, expected %d" % (result.get("n"), len(expected["features"])))
    if not same(collection, expected):
        problems.append(
            "the GeoJSON differs: got %s, expected %s" % (_short(collection, 400), _short(expected, 400))
        )
    return problems


def _check_affine(out: OutAffine, result: dict[str, Any]) -> list[str]:
    problems = []
    if not same(result.get("matrix_yx"), out.matrix):
        problems.append("matrix %s, expected %s" % (_short(result.get("matrix_yx")), _short(out.matrix)))
    extra = {k: v for k, v in result.items() if k not in ("type", "name", "matrix_yx")}
    if extra != out.display:
        problems.append("display keys %s, expected %s" % (extra, out.display))
    return problems


# ---- outlines: rasterise the polygons back (an even-odd test written here, not the production one)
def rasterise(feature: dict[str, Any], shape: tuple[int, int]) -> np.ndarray:
    """Pixels whose centre (integer row, column) lies inside the Polygon / MultiPolygon, rings of [x, y]; holes by even-odd."""
    rows, columns = np.mgrid[0 : shape[0], 0 : shape[1]]
    geometry = feature["geometry"]
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    inside = np.zeros(shape, dtype=bool)
    for polygon in polygons:
        part = np.zeros(shape, dtype=bool)
        for ring in polygon:
            part ^= _ring_mask(ring, rows, columns)
        inside |= part
    return inside


def _ring_mask(ring: list[list[float]], rows: np.ndarray, columns: np.ndarray) -> np.ndarray:
    mask = np.zeros(rows.shape, dtype=bool)
    for (x1, y1), (x2, y2) in zip(ring[:-1], ring[1:]):
        if y1 == y2:
            continue
        crosses = (y1 > rows) != (y2 > rows)
        x_at = x1 + (rows - y1) * (x2 - x1) / (y2 - y1)
        mask ^= crosses & (columns < x_at)
    return mask


def _check_outlines(out: OutOutlines, result: dict[str, Any]) -> list[str]:
    collection = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    labels = np.asarray(out.labels)
    wanted = {int(v): int((labels == v).sum()) for v in np.unique(labels) if v != 0}
    wanted = {label: area for label, area in wanted.items() if area >= out.min_area}
    problems = []
    features = {f["properties"]["label"]: f for f in collection["features"]}
    if len(features) != len(collection["features"]):
        problems.append("a label has more than one feature")
    if sorted(features) != sorted(wanted):
        return problems + ["labels %s, expected %s" % (sorted(features), sorted(wanted))]
    if result.get("n") != len(wanted):
        problems.append("n = %r, expected %d" % (result.get("n"), len(wanted)))
    for label, feature in features.items():
        if feature["properties"].get("area") != wanted[label]:
            problems.append(
                "label %d: area %r, expected %d" % (label, feature["properties"].get("area"), wanted[label])
            )
        for polygon in (
            [feature["geometry"]["coordinates"]]
            if feature["geometry"]["type"] == "Polygon"
            else feature["geometry"]["coordinates"]
        ):
            for ring in polygon:
                if ring[0] != ring[-1] or len(ring) < 4:
                    problems.append("label %d: a ring is not closed with at least 3 vertices" % label)
        back = rasterise(feature, labels.shape)
        wrong = int(np.count_nonzero(back != (labels == label)))
        if wrong > out.slack:
            problems.append(
                "label %d: the outline rasterises to %d pixels that differ from the label (allowed %d)"
                % (label, wrong, out.slack)
            )
    return problems


# ------------------------------------------------------------------------------------------------ one case
def run_case(session: Session, transport: str, case: Case) -> list[str]:
    """Run `case` through `transport` and return the problems (an empty list means the round trip held)."""
    folder = session.case_dir()
    wire, sent = session.materialise(case, folder)
    got = RUNNERS[transport](session, case, wire, folder)
    problems = check(session, case, got, sent)
    if got.job_dir and transport in ("snippet",) and Path(got.job_dir).is_dir():
        shutil.rmtree(
            got.job_dir, ignore_errors=True
        )  # a snippet gives the worker's own temporary folder to the caller
    shutil.rmtree(folder, ignore_errors=True)
    return problems
