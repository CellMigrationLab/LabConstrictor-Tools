"""The `runs`, `kernel`, `oracle` and `sideeffects` checks: start the app's kernel for ONE notebook, run the cells top to bottom with nbclient (allow_errors, per-cell
timeout), inject the click-script stages after the cells the script names, then run the oracle. Everything is cell by cell so that a failing cell is its own row.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import nb_sidefx
import nbformat
from nb_common import Notebook, check_id, sanitise
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError

KERNEL_SOURCE = (Path(__file__).with_name("lcnb_kernel.py")).read_text(encoding="utf-8")
BOOT = """
import sys, types
_m = types.ModuleType("lcnb")
exec(compile(%(src)r, "lcnb_kernel.py", "exec"), _m.__dict__)
sys.modules["lcnb"] = _m
get_ipython().user_ns["lcnb"] = _m
_m.LINES_PATH = %(lines)r
_m.install_audit(%(log)r, %(watch)r, %(ignore)r)
print("LCNB INFO python", sys.executable, sys.prefix)
"""
APP_COPY_IGNORE = shutil.ignore_patterns(
    "src", "build", "*.egg-info", "*.png", "*.ico", "*.icns", ".git", "__pycache__"
)


@dataclass
class Ctx:
    """What a click script and its oracle get: paths and small helpers (the worker runs in the app's interpreter, `run_python` uses it too)."""

    app: str
    notebook: str
    prefix: Path
    src: Path
    tag: str
    results: Path
    lc_home: str
    home: Path
    work: Path
    cwd: Path
    kernel_state: dict[str, Any] = field(default_factory=dict)

    def run_python(
        self, args: list[str], timeout: int = 300, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or self.work,
            errors="replace",
        )

    def copy_of(self, relative: str) -> Path:
        """A copy of `src/<relative>` under the scratch work folder (the checkout itself is never touched)."""
        target = self.work / Path(relative).name
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(self.src / relative, target)
        return target


class Run:
    """The state of one notebook run: counts and the failing cells."""

    def __init__(self) -> None:
        self.failed_cells: list[str] = []
        self.stage_failures: list[str] = []
        self.executed = 0
        self.dead = False
        self.oracle_rows: list[tuple[str, str]] = []
        self.lines_path: Path | None = None
        self.lines_offset = 0

    def new_lines(self) -> list[tuple[str, str, str, str]]:
        """The result lines the kernel-side helpers wrote since the last call: (kind, ident, verdict, detail)."""
        if self.lines_path is None or not self.lines_path.is_file():
            return []
        text = self.lines_path.read_text(encoding="utf-8")
        fresh = text[self.lines_offset :]
        self.lines_offset = len(text)
        found = []
        for line in fresh.splitlines():
            item = json.loads(line)
            found.append((item["kind"], item["ident"], item["verdict"], item["detail"]))
        return found


def _lcnb_lines(outputs: list[Any]) -> list[tuple[str, str, str, str]]:
    """(kind, ident, verdict, detail) of every `LCNB ...` line printed by a cell."""
    found = []
    for output in outputs:
        if output.get("output_type") != "stream":
            continue
        for line in "".join(output.get("text", "")).splitlines():
            if line.startswith("LCNB "):
                bits = line.split(" ", 4)
                found.append(
                    (
                        bits[1],
                        bits[2] if len(bits) > 2 else "",
                        bits[3] if len(bits) > 3 else "",
                        bits[4] if len(bits) > 4 else "",
                    )
                )
    return found


def _error_of(cell: Any) -> str | None:
    for output in cell.get("outputs", []):
        if output.get("output_type") == "error":
            return "%s: %s" % (output.get("ename"), str(output.get("evalue"))[:300])
    return None


async def _execute(
    client: NotebookClient, cell: Any, index: int, run: Run, label: str
) -> tuple[str | None, bool]:
    """Run one cell; returns (error text or None, kernel_is_dead). Timeouts, a dead kernel and nbclient errors are results, never raised."""
    started = time.time()
    try:
        await client.async_execute_cell(cell, index)
    except CellTimeoutError:
        return "timeout after %s s in %s (kernel interrupted)" % (client.timeout, label), False
    except DeadKernelError:
        return "the kernel died while running %s" % label, True
    except CellExecutionError as problem:
        return "CellExecutionError: %s" % str(problem)[:300], False
    run.executed += 1
    error = _error_of(cell)
    if (
        error
        and error.startswith("KeyboardInterrupt")
        and time.time() - started >= float(client.timeout or 0) - 1
    ):
        error = "timeout after %s s in %s (nbclient interrupted the cell): %s" % (
            client.timeout,
            label,
            error,
        )
    return error, False


def _inject(client: NotebookClient, source: str) -> tuple[Any, int]:
    """Append a harness cell (a click stage, the boot cell, the oracle cell) to the notebook being run and return it with its index: nbclient addresses cells by
    index. The executed notebook saved at the end therefore shows every stage with its output."""
    cell = nbformat.v4.new_code_cell(source)
    client.nb.cells.append(cell)
    return cell, len(client.nb.cells) - 1


async def _run_stage(client: NotebookClient, emit: Any, run: Run, name: str, code: str) -> bool:
    """Run one click stage; returns kernel_is_dead. Lines it prints become rows, an exception becomes the FAIL row `click_<stage>`."""
    cell, index = _inject(client, code)
    started = time.time()
    error, dead = await _execute(client, cell, index, run, "click stage " + name)
    for kind, ident, verdict, detail in run.new_lines():
        status = verdict if kind == "CHECK" else kind if kind in ("HUMAN", "NOTE") else "FAIL"
        emit.row(ident, status, detail, full_id=check_id(emit.app, emit.notebook, ident))
        if status == "FAIL":
            run.stage_failures.append(ident)
        if ident.startswith("oracle_"):
            run.oracle_rows.append((ident, status))
    if error:
        run.stage_failures.append(name)
        emit.row("click_" + name, "FAIL", error, time.time() - started)
    return dead


async def run_notebook(
    emit: Any,
    args: Any,
    notebook: Notebook,
    installed: Path,
    home: Path,
    script: ModuleType | None,
    spec_name: str,
) -> None:
    prefix, results = Path(args.prefix), Path(args.results)
    assert os.environ.get("HOME") == str(home), "worker HOME %r is not the scratch home %s" % (
        os.environ.get("HOME"),
        home,
    )
    run = Run()
    started = time.time()
    if not installed.is_file():
        emit.row("runs", "FAIL", "notebook not installed, not run: %s" % installed)
        emit.row("kernel", "NOT_RUN", "notebook not installed")
        emit.row("oracle", "FAIL", "notebook not installed")
        emit.row("sideeffects", "NOTE", "notebook not run")
        return
    app_dir = prefix / notebook.installed_rel.split("/")[0]
    appcopy = home / "appcopy" / app_dir.name
    shutil.rmtree(appcopy, ignore_errors=True)
    shutil.copytree(app_dir, appcopy, ignore=APP_COPY_IGNORE)
    cwd = appcopy / Path(notebook.installed_rel).parent.relative_to(app_dir.name)
    work = home / "work"
    work.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(
        args.app, notebook.name, prefix, Path(args.src), args.tag, results, args.lc_home, home, work, cwd
    )
    log_path = home / "side_audit.jsonl"
    log_path.unlink(missing_ok=True)
    run.lines_path = home / "lcnb_lines.jsonl"
    run.lines_path.unlink(missing_ok=True)
    before = nb_sidefx.snapshot(app_dir)
    home_before = set(nb_sidefx.snapshot(home))

    document = nbformat.read(
        str(appcopy / Path(notebook.installed_rel).relative_to(app_dir.name)), as_version=4
    )
    if script is not None and hasattr(script, "edit_cells"):
        _apply_edits(emit, document, script.edit_cells(ctx))
    timeout = int(os.environ.get("LC_NB_CELL_TIMEOUT", "300"))
    client = NotebookClient(
        document,
        timeout=timeout,
        allow_errors=True,
        interrupt_on_timeout=True,
        startup_timeout=180,
        kernel_name=spec_name,
        resources={"metadata": {"path": str(cwd)}},
    )
    inputs = (
        guarded_call(emit, "inputs", lambda: script.inputs(ctx))
        if script is not None and hasattr(script, "inputs")
        else {}
    )
    after_cell: dict[int, str] = dict(getattr(script, "AFTER_CELL", {})) if script else {}
    stages: dict[str, str] = dict(getattr(script, "STAGES", {})) if script else {}
    auto_all: bool = bool(getattr(script, "AUTO_DRIVE_ALL", False)) if script else False
    auto_tick: tuple[str, ...] = tuple(getattr(script, "AUTO_TICK", ())) if script else ()
    auto_skip: tuple[str, ...] = tuple(getattr(script, "AUTO_SKIP", ())) if script else ()
    human_cells: dict[int, str] = dict(getattr(script, "HUMAN_CELLS", {})) if script else {}
    original_count = len(document.cells)
    async with client.async_setup_kernel():
        boot = BOOT % {
            "src": KERNEL_SOURCE,
            "log": str(log_path),
            "watch": [str(prefix), os.environ.get("ORIGINAL_HOME", "/root")],
            "ignore": [str(home)],
            "lines": str(run.lines_path),
        }
        cell, boot_index = _inject(client, boot)
        error, dead = await _execute(client, cell, boot_index, run, "the harness boot cell")
        lines = _lcnb_lines(cell.outputs)
        python = next((v for k, i, v, d in lines if k == "INFO" and i == "python"), None) if lines else None
        _kernel_row(emit, python, prefix, spec_name, error)
        inject, inject_index = _inject(
            client, "import json\nlcnb.INPUTS.update(json.loads(%r))" % json.dumps(inputs, default=str)
        )
        await _execute(client, inject, inject_index, run, "the inputs cell")
        for index in range(original_count):
            cell = document.cells[index]
            if dead:
                if cell.cell_type == "code" and cell.source.strip():
                    run.failed_cells.append(str(index))
                    emit.row("cell_%d" % index, "NOT_RUN", "not run: the kernel died earlier")
                continue
            if cell.cell_type != "code" or not cell.source.strip():
                continue
            if index in human_cells:
                emit.row("human_cell_%d" % index, "HUMAN", human_cells[index])
                continue
            cell_started = time.time()
            error, dead = await _execute(client, cell, index, run, "cell %d" % index)
            if error:
                run.failed_cells.append(str(index))
                emit.row("cell_%d" % index, "FAIL", error, time.time() - cell_started)
            if index in after_cell and not dead:
                dead = await _run_stage(client, emit, run, after_cell[index], stages[after_cell[index]])
            elif auto_all and not dead:
                dead = await _run_stage(
                    client,
                    emit,
                    run,
                    "auto%d" % index,
                    "lcnb.tick(%r)\nlcnb.auto_drive(%r, skip=%r)" % (auto_tick, "c%d" % index, auto_skip),
                )
        run.dead = dead
        if script is not None and getattr(script, "ORACLE_KERNEL", "") and not dead:
            dead = await _run_stage(client, emit, run, "oracle_kernel", script.ORACLE_KERNEL)
    _finish(emit, run, ctx, script, document, results, home, before, app_dir, home_before, log_path, started)


def _apply_edits(emit: Any, document: Any, edits: dict[int, list[tuple[str, str]]]) -> None:
    """Edits a user must make by hand before the notebook can run (a placeholder path in a configuration cell). Each is a NOTE row; a target that is not in the cell is a FAIL."""
    for index, pairs in edits.items():
        for old, new in pairs:
            source = document.cells[index].source
            if old not in source:
                emit.row(
                    "edit_cell_%d" % index,
                    "FAIL",
                    "the script expects %r in cell %d but it is not there (the notebook changed?)"
                    % (old, index),
                )
                continue
            document.cells[index].source = source.replace(old, new)
            emit.row(
                "edit_cell_%d" % index,
                "NOTE",
                "cell %d edited as a user would, before running: %r replaced by %r" % (index, old, new),
            )


def guarded_call(emit: Any, step: str, action: Any) -> Any:
    try:
        return action()
    except Exception as problem:  # a broken script input is visible, and the run goes on with no inputs
        emit.row(step, "FAIL", "script %s() raised %s: %s" % (step, type(problem).__name__, problem))
        return {}


def _kernel_row(emit: Any, python: str | None, prefix: Path, spec_name: str, error: str | None) -> None:
    expected = prefix / "bin" / "python"
    if python is None:
        emit.row("kernel", "FAIL", "the kernel did not report its interpreter (%s)" % (error or "no output"))
    elif os.path.realpath(python) == os.path.realpath(expected):
        emit.row("kernel", "PASS", "live kernel %r runs %s (the app's interpreter)" % (spec_name, python))
    else:
        emit.row("kernel", "FAIL", "live kernel runs %s, not the app's %s" % (python, expected))


def _finish(
    emit: Any,
    run: Run,
    ctx: Ctx,
    script: ModuleType | None,
    document: Any,
    results: Path,
    home: Path,
    before: dict[str, int],
    app_dir: Path,
    home_before: set[str],
    log_path: Path,
    started: float,
) -> None:
    executed_dir = results / ctx.app / "executed"
    executed_dir.mkdir(parents=True, exist_ok=True)
    nbformat.write(document, str(executed_dir / (sanitise(ctx.notebook) + ".ipynb")))
    problems = run.failed_cells + run.stage_failures
    detail = (
        "%d cells and stages executed; failing cells: %s; failing click stages/assertions: %s; executed notebook: %s"
        % (
            run.executed,
            ", ".join(run.failed_cells) or "none",
            ", ".join(run.stage_failures) or "none",
            executed_dir / (sanitise(ctx.notebook) + ".ipynb"),
        )
    )
    emit.row(
        "runs",
        "FAIL" if problems or run.dead else "PASS",
        ("kernel died; " if run.dead else "") + detail,
        time.time() - started,
    )
    _oracle(emit, run, ctx, script)
    created, changed, removed = nb_sidefx.diff(before, nb_sidefx.snapshot(app_dir))
    home_created = sorted(set(nb_sidefx.snapshot(home)) - home_before)
    text = nb_sidefx.summarise(
        nb_sidefx.read_log(log_path), (created, changed, removed), home_created, str(app_dir)
    )
    report = results / ctx.app / ("sideeffects_%s.txt" % sanitise(ctx.notebook))
    report.write_text(text + "\n", encoding="utf-8")
    for number, event in enumerate(e for e in nb_sidefx.read_log(log_path) if e["kind"] == "http"):
        emit.row(
            "net_%d" % number,
            "NOTE",
            "%s %s -> %s (size %s bytes)"
            % (
                event["method"],
                event["url"],
                event.get("status", "FAILED: " + str(event.get("error"))),
                event.get("size", "n/a"),
            ),
        )
    emit.row(
        "sideeffects",
        "NOTE",
        "app folder created %d, changed %d, removed %d files; %s"
        % (len(created), len(changed), len(removed), text[:220])
        + " (full: %s)" % report,
    )


def _oracle(emit: Any, run: Run, ctx: Ctx, script: ModuleType | None) -> None:
    """Host-side oracle rows `oracle_<ident>` and the aggregate `oracle` row (HUMAN when the script says no oracle is possible)."""
    if script is None:
        emit.row(
            "oracle",
            "FAIL",
            "no click script scripts/%s/%s.py: the notebook has neither a click workflow nor an oracle"
            % (ctx.app, ctx.notebook),
        )
        return
    if hasattr(script, "oracle"):
        try:
            for ident, status, detail in script.oracle(ctx):
                emit.row("oracle_" + ident, status, detail)
                run.oracle_rows.append(("oracle_" + ident, status))
        except Exception as problem:  # an oracle that crashes is a failed oracle
            emit.row("oracle_error", "FAIL", "oracle raised %s: %s" % (type(problem).__name__, problem))
            run.oracle_rows.append(("oracle_error", "FAIL"))
    reason = getattr(script, "NO_ORACLE", "")
    if reason and not run.oracle_rows:
        emit.row("oracle", "HUMAN", reason)
    elif not run.oracle_rows:
        emit.row("oracle", "FAIL", "the script produced no oracle assertion")
    else:
        bad = [i for i, s in run.oracle_rows if s == "FAIL"]
        human = [i for i, s in run.oracle_rows if s == "HUMAN"]
        if bad:
            emit.row("oracle", "FAIL", "failing: " + ", ".join(bad))
        elif human:
            emit.row("oracle", "HUMAN", "part of the outcome needs a person: " + ", ".join(human))
        else:
            emit.row("oracle", "PASS", "%d outcome assertions passed" % len(run.oracle_rows))
