"""Negative controls of the notebook family: SEEDED failures that must go red (and a good notebook that must go green), run through the real nb_runner.py on a
fake app (a throw-away prefix whose bin/python is the app interpreter of Guess the Condition, a git checkout with a release tag, seeded notebooks and scripts).

    python test_nb_runner.py        (prints every expectation and the matrix row it came from; exit 1 if the runner misses a seeded failure)
    pytest test_nb_runner.py

Seeded: a bad import, a cell that raises, a hanging cell (timeout), a cell that ignores the interrupt (outer watchdog), a widget that is never found, a packaged notebook
differing by one cell, a notebook that needs a native file dialog (HUMAN), a notebook that runs without errors but does the wrong thing (oracle must fail)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
APP_PREFIX = Path(os.environ.get("LC_NB_TEST_PREFIX", "/home/user/apps/GuessTheCondition"))
APP = "NegControl"


def nb_json(cells: list[tuple[str, str]], outputs: bool = False, kernel: str = "python3") -> str:
    """A minimal valid nbformat 4.5 notebook: (cell_type, source) per cell."""
    document: dict[str, Any] = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": {"name": kernel, "display_name": "Python 3", "language": "python"}}, "cells": []}
    for index, (kind, source) in enumerate(cells):
        cell: dict[str, Any] = {"cell_type": kind, "id": "c%d" % index, "metadata": {}, "source": source.splitlines(keepends=True)}
        if kind == "code":
            cell.update({"outputs": [{"output_type": "stream", "name": "stdout", "text": ["old output\n"]}] if outputs else [], "execution_count": 3 if outputs else None})
        document["cells"].append(cell)
    return json.dumps(document, indent=1)


GOOD = [("markdown", "# good"), ("code", "import ipywidgets as w\nout = []\nb = w.Button(description='Press')\nb.on_click(lambda _: out.append(1))\nt = w.Text(description='Name')"), ("code", "print('fine')")]
NOTEBOOKS: dict[str, list[tuple[str, str]]] = {
    "good": GOOD,
    "bad_import": [("code", "import definitely_not_a_module_xyz\nprint('unreachable')")],
    "raises": [("code", "print('before')"), ("code", "raise ValueError('seeded failure')"), ("code", "print('after: the run goes on')")],
    "hangs": [("code", "import time\ntime.sleep(600)"), ("code", "print('after the timeout')")],
    "ignores_interrupt": [("code", "import signal\nsignal.signal(signal.SIGINT, signal.SIG_IGN)\nwhile True:\n    pass")],
    "widget_missing": [("code", "import ipywidgets as w\nb = w.Button(description='Real button')")],
    "differs": [("code", "print('same')"), ("code", "print('the release says one thing')")],
    "file_dialog": [("code", "from tkinter import filedialog\npath = filedialog.askopenfilename()")],
    "wrong_outcome": [("code", "print('writes nothing at all')")],
    "stale_kernel": [("code", "print('runs on a kernelspec that points to another interpreter')")],
    "auto_buttons": [("markdown", "# buttons"), ("code", "import ipywidgets as w\nfrom IPython.display import display\n"
                      "def bad(_):\n    raise RuntimeError('seeded handler failure')\n"
                      "ok = w.Button(description='Press ok'); ok.on_click(lambda _: print('did it'))\n"
                      "broken = w.Button(description='Broken'); broken.on_click(bad)\n"
                      "from ipywidgets import Output\nout = Output()\n"
                      "captured = w.Button(description='Captured broken'); captured.on_click(out.capture()(bad))\n"
                      "picker = w.Button(description='Find folder')\ndisplay(ok, broken, captured, picker)")],
}
SCRIPTS = {
    "good": 'AFTER_CELL = {1: "go"}\nSTAGES = {"go": """\nlcnb.set_value(lcnb.find(kind="Text", description="Name"), "x")\nlcnb.click(lcnb.find(kind="Button", description="Press"))\nlcnb.check("oracle_clicked", get_ipython().user_ns["out"] == [1], "the click handler ran")\n"""}\n',
    "widget_missing": 'AFTER_CELL = {0: "go"}\nSTAGES = {"go": "lcnb.click(lcnb.find(kind=\'Button\', description=\'Button that does not exist\'))"}\nNO_ORACLE = "none"\n',
    "file_dialog": 'HUMAN_CELLS = {0: "native file dialog (tkinter askopenfilename) needs a display and a person"}\nNO_ORACLE = "the outcome is the file a person picks"\n',
    "wrong_outcome": 'from pathlib import Path\ndef oracle(ctx):\n    target = ctx.work / "result.csv"\n    return [("file_written", "PASS" if target.is_file() else "FAIL", "expected %s to be written by the notebook" % target)]\n',
    "bad_import": 'NO_ORACLE = "none"\n',
    "raises": 'NO_ORACLE = "none"\n',
    "hangs": 'NO_ORACLE = "none"\n',
    "ignores_interrupt": 'NO_ORACLE = "none"\n',
    "differs": 'NO_ORACLE = "none"\n',
    "stale_kernel": 'NO_ORACLE = "none"\n',
    "auto_buttons": 'AUTO_DRIVE_ALL = True\nNO_ORACLE = "none"\n',
}


def build(root: Path) -> tuple[Path, Path, Path, Path]:
    """(prefix, src, scripts, results) of the fake app; src is a git checkout at tag 0.0.1."""
    prefix, src, scripts, results = root / "prefix", root / "src", root / "scripts" / APP, root / "results"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "bin" / "python").symlink_to(APP_PREFIX / "bin" / "python")
    kernel = prefix / "share" / "jupyter" / "kernels" / "python3"
    kernel.mkdir(parents=True)
    spec = json.loads((APP_PREFIX / "share/jupyter/kernels/python3/kernel.json").read_text(encoding="utf-8"))
    spec["argv"][0] = str(prefix / "bin" / "python")
    (kernel / "kernel.json").write_text(json.dumps(spec), encoding="utf-8")
    other = root / "other_python"
    other.write_text('#!/bin/sh\nexec %s "$@"\n' % (APP_PREFIX / "bin" / "python"), encoding="utf-8")
    other.chmod(0o755)
    stale = prefix / "share" / "jupyter" / "kernels" / "stale"
    stale.mkdir(parents=True)
    (stale / "kernel.json").write_text(json.dumps(dict(spec, argv=[str(other)] + spec["argv"][1:])), encoding="utf-8")
    scripts.mkdir(parents=True)
    extra = []
    for name, cells in NOTEBOOKS.items():
        released = cells if name != "differs" else [cells[0], ("code", "print('the release says another thing')")]
        (src / "notebooks" / name).mkdir(parents=True)
        (src / "notebooks" / name / (name + ".ipynb")).write_text(nb_json(released), encoding="utf-8")
        (prefix / "Fake" / "notebooks" / name).mkdir(parents=True)
        (prefix / "Fake" / "notebooks" / name / (name + ".ipynb")).write_text(nb_json(cells, outputs=name == "good", kernel="stale" if name == "stale_kernel" else "python3"), encoding="utf-8")
        extra.append("- notebooks/%s/%s.ipynb: Fake/notebooks/%s/%s.ipynb" % (name, name, name, name))
        (scripts / (name + ".py")).write_text(SCRIPTS[name], encoding="utf-8")
    (src / "construct.yaml").write_text("name: Fake\nextra_files:\n" + "\n".join(extra) + "\n", encoding="utf-8")
    for command in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "release"], ["tag", "0.0.1"]):
        subprocess.run(["git", "-C", str(src), *command], check=True, capture_output=True)
    return prefix, src, root / "scripts", results


def run_controls() -> dict[str, dict[str, str]]:
    """Run the real runner on the fake app and return {row id: {status, detail}}; the workspace is deleted afterwards."""
    root = Path(tempfile.mkdtemp(prefix="nb_negative_"))
    try:
        prefix, src, scripts, results = build(root)
        env = dict(os.environ, LC_NB_CELL_TIMEOUT="6", LC_NB_TOTAL_TIMEOUT="45", LC_NB_SCRIPTS=str(scripts))
        done = subprocess.run(
            [sys.executable, str(HERE / "nb_runner.py"), "--app", APP, "--prefix", str(prefix), "--src", str(src), "--tag", "0.0.1", "--results", str(results), "--lc-home", str(root / "lc_home")],
            env=env, capture_output=True, text=True, timeout=900,
        )
        matrix = json.loads((results / APP / ("matrix_nb_notebook_%s.json" % APP)).read_text(encoding="utf-8"))
        rows = {r["id"]: {"status": r["status"], "detail": r["detail"]} for r in matrix["rows"]}
        rows["_stdout"] = {"status": "", "detail": done.stdout[-400:] + done.stderr[-400:]}
        return rows
    finally:
        shutil.rmtree(root, ignore_errors=True)


def expectations() -> list[tuple[str, str, str]]:
    """(row id, expected status, what the seeded failure is)."""
    def i(nb: str, check: str) -> str:
        return "nb_%s_%s_%s" % (APP, nb, check)

    return [
        (i("good", "packaged"), "PASS", "control: installed notebook with outputs cleared and other metadata equals the release by cells"),
        (i("good", "valid"), "PASS", "control: nbformat valid and the kernel resolves to the app interpreter"),
        (i("good", "imports"), "PASS", "control: imports resolve"),
        (i("good", "runs"), "PASS", "control: runs, the scripted click and type work"),
        (i("good", "oracle"), "PASS", "control: the oracle sees the effect of the click"),
        (i("good", "kernel"), "PASS", "control: live kernel is the app interpreter"),
        (i("good", "noleak"), "PASS", "control: no kernel left over"),
        (i("bad_import", "imports"), "FAIL", "seeded bad import"),
        (i("bad_import", "cell_0"), "FAIL", "seeded bad import also fails when run"),
        (i("raises", "cell_1"), "FAIL", "seeded cell that raises"),
        (i("raises", "runs"), "FAIL", "seeded cell that raises makes the run red"),
        (i("hangs", "cell_0"), "FAIL", "seeded hanging cell is a timeout row"),
        (i("hangs", "runs"), "FAIL", "seeded hanging cell makes the run red"),
        (i("ignores_interrupt", "watchdog"), "FAIL", "a cell that ignores the interrupt is killed by the outer watchdog"),
        (i("ignores_interrupt", "runs"), "FAIL", "watchdog writes the runs FAIL row"),
        (i("ignores_interrupt", "noleak"), "PASS", "after the watchdog kill no kernel is left"),
        (i("widget_missing", "click_go"), "FAIL", "seeded widget that is never found"),
        (i("widget_missing", "runs"), "FAIL", "widget never found makes the run red"),
        (i("differs", "packaged"), "FAIL", "packaged notebook differing by one cell"),
        (i("file_dialog", "human_cell_0"), "HUMAN", "native file dialog is HUMAN"),
        (i("file_dialog", "oracle"), "HUMAN", "no oracle for a native file dialog is HUMAN, never PASS"),
        (i("stale_kernel", "valid"), "FAIL", "the KERNEL TRAP: a kernelspec resolving to another interpreter than the app's"),
        (i("auto_buttons", "click_auto_c1_Press_ok"), "PASS", "auto-drive presses a plain button"),
        (i("auto_buttons", "click_auto_c1_Broken"), "FAIL", "a button handler that raises is a FAIL (ipywidgets would swallow it)"),
        (i("auto_buttons", "click_auto_c1_Captured_broken"), "FAIL", "a handler wrapped in Output.capture() that raises is a FAIL too (the widget swallows it)"),
        (i("auto_buttons", "click_auto_c1_Find_folder"), "HUMAN", "a native folder picker button is HUMAN, never clicked"),
        (i("auto_buttons", "runs"), "FAIL", "the seeded handler failure makes the run red"),
        (i("hangs", "kernel"), "PASS", "control: the live kernel is checked for every notebook"),
        (i("wrong_outcome", "runs"), "PASS", "no cell errors in the wrong-outcome notebook"),
        (i("wrong_outcome", "oracle"), "FAIL", "a notebook that runs clean but does nothing fails the oracle"),
    ]


def main() -> int:
    rows = run_controls()
    bad = 0
    for row_id, wanted, why in expectations():
        got = rows.get(row_id, {"status": "MISSING", "detail": ""})
        ok = got["status"] == wanted
        bad += not ok
        print("%s %-6s (expected %-5s) %s | %s | %s" % ("ok  " if ok else "WRONG", got["status"], wanted, row_id, why, got["detail"][:110]))
    print("negative controls: %d of %d as expected" % (len(expectations()) - bad, len(expectations())))
    return 1 if bad else 0


def test_negative_controls() -> None:
    rows = run_controls()
    wrong = [(r, w, rows.get(r, {}).get("status")) for r, w, _ in expectations() if rows.get(r, {}).get("status") != w]
    assert not wrong, "controls not as expected (id, wanted, got): %s | %s" % (wrong, rows["_stdout"])


if __name__ == "__main__":
    sys.exit(main())
