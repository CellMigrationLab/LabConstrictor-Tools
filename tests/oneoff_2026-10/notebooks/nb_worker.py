"""Worker of the notebook family: ONE notebook of ONE app, run with the app's own interpreter (nbclient, nbformat and ipykernel come from the app's environment).

    <prefix>/bin/python nb_worker.py --app A --prefix P --src S --tag T --results R --lc-home H --notebook N --rows FILE

Every result is a JSON line appended to --rows as it happens (the parent turns the lines into matrix rows, so a kill loses nothing already written). Every
step is guarded: an unexpected exception becomes a FAIL row naming it ("runner error"), never a stop."""

import argparse
import asyncio
import importlib.util
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scripts"))  # shared scripts such as _welcome.py

import nb_checks  # noqa: E402
import nb_imports  # noqa: E402
import nb_kernel_run  # noqa: E402
from nb_common import Notebook, check_id, discover, sanitise, script_path  # noqa: E402


class Emitter:
    """Appends result rows as JSON lines; `row(check, status, detail)` takes the short check name and builds the full id."""

    def __init__(self, path: Path, app: str, notebook: str) -> None:
        self.path, self.app, self.notebook = path, app, notebook

    def row(self, check: str, status: str, detail: str = "", seconds: float = 0.0, full_id: str | None = None) -> None:
        line = {"id": full_id or check_id(self.app, self.notebook, check), "status": status, "detail": detail, "seconds": round(seconds, 2)}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line) + "\n")


def load_script(app: str, notebook: str) -> ModuleType | None:
    """The click script scripts/<app>/<notebook>.py, or None when there is none (the caller records that as a FAIL: a missing script is a gap)."""
    path = script_path(Path(os.environ.get("LC_NB_SCRIPTS", str(HERE / "scripts"))), app, notebook)
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("nbscript_%s_%s" % (sanitise(app), sanitise(notebook)), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guarded(emit: Emitter, step: str, action: Any) -> Any:
    try:
        return action()
    except Exception as problem:  # runner bug or environment: always visible in the matrix
        emit.row(step, "FAIL", "runner error in %s: %s: %s | %s" % (step, type(problem).__name__, problem, traceback.format_exc().splitlines()[-4:]))
        traceback.print_exc()
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("app", "prefix", "src", "tag", "results", "lc-home", "notebook", "rows"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    emit = Emitter(Path(args.rows), args.app, args.notebook)
    prefix, src, results = Path(args.prefix), Path(args.src), Path(args.results)
    notebook = next(n for n in discover(src) if n.name == args.notebook)
    home = results / args.app / ("home_" + sanitise(notebook.name))
    installed = prefix / notebook.installed_rel

    started = time.time()
    guarded(emit, "packaged", lambda: nb_checks.packaged(emit, installed, src / notebook.src_rel))
    spec_name = guarded(emit, "valid", lambda: nb_checks.valid(emit, installed, prefix))
    guarded(emit, "imports", lambda: run_imports(emit, installed, prefix, home, args.lc_home))
    script = guarded(emit, "oracle", lambda: load_script(args.app, notebook.name))
    guarded(emit, "runs", lambda: asyncio.run(nb_kernel_run.run_notebook(emit, args, notebook, installed, home, script, spec_name or "python3")))
    emit.row("worker_done", "NOTE", "worker finished in %.0f s" % (time.time() - started), time.time() - started)
    return 0


def run_imports(emit: Emitter, installed: Path, prefix: Path, home: Path, lc_home: str) -> None:
    from nb_common import read_cells, worker_env

    started = time.time()
    if not installed.is_file():
        emit.row("imports", "FAIL", "notebook not installed, imports not checked: %s" % installed)
        return
    refs, problems = nb_imports.extract(read_cells(installed))
    home.mkdir(parents=True, exist_ok=True)
    timeout = int(os.environ.get("LC_NB_IMPORT_TIMEOUT", "300"))
    results = nb_imports.probe(refs, sys.executable, worker_env(prefix, home, lc_home), home, timeout)
    kinds = {(r.module, tuple(r.names)): r.kind for r in refs}
    failed, notes = list(problems), []
    for result in results:
        if result["status"] == "ok":
            continue
        kind = kinds.get((result["module"], tuple(result.get("names", []))), "required")
        text = "%s (%s): %s" % (result["module"], kind, result["error"])
        (failed if kind == "required" else notes).append(text)
    detail = "%d imports resolved in %s" % (len(results) - len(failed) - len(notes), sys.executable)
    if notes:
        detail += "; optional or Colab-only unresolved: " + "; ".join(notes)
    emit.row("imports", "FAIL" if failed else "PASS", ("; ".join(failed) + " | " if failed else "") + detail, time.time() - started)


if __name__ == "__main__":
    sys.exit(main())
