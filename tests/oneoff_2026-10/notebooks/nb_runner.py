"""Family `nb` of the one-off run: every notebook an installed app packages is checked (packaged, valid, kernel, imports, runs with simulated clicks, oracle),
every step guarded, nothing stops at a failure.

    python nb_runner.py --app NAME --prefix PREFIX --src SRC_CHECKOUT --tag TAG --results DIR --lc-home LC_HOME [--only NOTEBOOK[,NOTEBOOK]]

One worker process per notebook (nb_worker.py, started with the APP's interpreter so that nbclient, ipykernel and the kernel come from the app's environment),
one kernel per notebook, an outer watchdog (LC_NB_TOTAL_TIMEOUT seconds, default 3600) that kills a hung worker with its kernel, and a leak check that no kernel
of the notebook survives. The matrix is results/<app>/matrix_nb_notebook_<app>.json; the expected ids are written first, so anything not produced is NOT_RUN."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from matrix import Matrix  # noqa: E402
from nb_common import CHECKS, Notebook, check_id, discover, sanitise, worker_env  # noqa: E402

WORKER = HERE / "nb_worker.py"
TOTAL_TIMEOUT_S = int(os.environ.get("LC_NB_TOTAL_TIMEOUT", "3600"))


def expected_ids(app: str, notebooks: list[Notebook]) -> list[str]:
    ids = [check_id(app, "notebooks", "srctag"), check_id(app, "notebooks", "inventory")]
    for notebook in notebooks:
        ids += [check_id(app, notebook.name, check) for check in CHECKS]
    return ids


def source_checks(matrix: Matrix, app: str, prefix: Path, src: Path, tag: str, notebooks: list[Notebook]) -> None:
    """The checkout is the release (tag) and the installed prefix holds exactly the notebooks of construct.yaml."""
    git = subprocess.run(["git", "-C", str(src), "describe", "--tags", "--exact-match"], capture_output=True, text=True)
    described = git.stdout.strip()
    if git.returncode != 0:
        matrix.add(check_id(app, "notebooks", "srctag"), "FAIL", "the source checkout %s is not at an exact tag (%s); expected %s" % (src, git.stderr.strip()[:150], tag))
    elif described != tag:
        matrix.add(check_id(app, "notebooks", "srctag"), "FAIL", "the source checkout is at %s, expected %s" % (described, tag))
    else:
        matrix.add(check_id(app, "notebooks", "srctag"), "PASS", "the source checkout is at the release tag %s" % tag)
    app_dirs = sorted({n.installed_rel.split("/")[0] for n in notebooks})
    installed = {p.stem for d in app_dirs for p in (prefix / d / "notebooks").rglob("*.ipynb")} if all((prefix / d).is_dir() for d in app_dirs) else set()
    wanted = {n.name for n in notebooks}
    if installed == wanted:
        matrix.add(check_id(app, "notebooks", "inventory"), "PASS", "%d notebooks installed, the same as construct.yaml lists: %s" % (len(wanted), ", ".join(sorted(wanted))))
    else:
        matrix.add(check_id(app, "notebooks", "inventory"), "FAIL", "installed but not listed: %s; listed but not installed: %s" % (sorted(installed - wanted), sorted(wanted - installed)))


def processes_of(marker: str) -> list[int]:
    """Pids whose command line mentions `marker` (the scratch home of a notebook appears in its kernel's connection-file argument)."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        if marker in command:
            found.append(int(entry.name))
    return found


def drain(path: Path, offset: int, matrix: Matrix, notebook: str) -> tuple[int, bool]:
    """Add the worker's new JSON lines to the matrix; returns (new offset, worker_done seen)."""
    done = False
    if not path.is_file():
        return offset, done
    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read()
    complete = data[: data.rfind(b"\n") + 1]
    for line in complete.decode("utf-8", "replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            matrix.add("nb_runner_unreadable_line", "FAIL", "unreadable worker line: " + line[:120], notebook)
            continue
        if row["id"].endswith("_worker_done"):
            done = True
            continue
        matrix.add(row["id"], row["status"], row["detail"], notebook, seconds=row.get("seconds", 0.0))
    return offset + len(complete), done


def run_one(args: argparse.Namespace, matrix: Matrix, notebook: Notebook) -> None:
    app, results = args.app, Path(args.results)
    prefix = Path(args.prefix)
    home = results / app / ("home_" + sanitise(notebook.name))
    home.mkdir(parents=True, exist_ok=True)
    rows = results / app / "nb_work" / (sanitise(notebook.name) + ".rows.jsonl")
    rows.parent.mkdir(parents=True, exist_ok=True)
    rows.unlink(missing_ok=True)
    log = results / app / ("log_nb_%s.txt" % sanitise(notebook.name))
    env = worker_env(prefix, home, args.lc_home)
    env["ORIGINAL_HOME"] = os.environ.get("ORIGINAL_HOME", os.environ.get("HOME", "/root"))
    command = [str(prefix / "bin" / "python"), str(WORKER)]
    for name in ("app", "prefix", "src", "tag", "results", "lc-home"):
        command += ["--" + name, str(getattr(args, name.replace("-", "_")))]
    command += ["--notebook", notebook.name, "--rows", str(rows)]
    started, offset, done, killed = time.time(), 0, False, False
    with log.open("w", encoding="utf-8") as handle:
        try:
            process = subprocess.Popen(command, env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True, cwd=home)
        except OSError as problem:
            matrix.add(check_id(app, notebook.name, "runs"), "FAIL", "could not start the worker %s: %s" % (command[0], problem), notebook.name)
            return
        while process.poll() is None:
            offset, done = drain(rows, offset, matrix, notebook.name)
            if time.time() - started > TOTAL_TIMEOUT_S:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                killed = True
                break
            time.sleep(0.5)
    offset, done = drain(rows, offset, matrix, notebook.name)
    seconds = time.time() - started
    have_runs = any(r["id"] == check_id(app, notebook.name, "runs") for r in matrix.rows)
    if killed:
        matrix.add(check_id(app, notebook.name, "watchdog"), "FAIL", "the worker exceeded the watchdog of %d s and was killed with its kernel (log: %s)" % (TOTAL_TIMEOUT_S, log), notebook.name, seconds=seconds)
        if not have_runs:
            matrix.add(check_id(app, notebook.name, "runs"), "FAIL", "killed by the watchdog after %d s before the run finished" % TOTAL_TIMEOUT_S, notebook.name, seconds=seconds)
    elif process.returncode != 0 and not done:
        tail = log.read_text(encoding="utf-8", errors="replace")[-300:]
        matrix.add(check_id(app, notebook.name, "worker"), "FAIL", "the worker crashed with exit %s: %s" % (process.returncode, tail), notebook.name, seconds=seconds)
    leaked = processes_of(str(home / "runtime"))
    for pid in leaked:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            print("leaked pid %d was already gone" % pid)
    if leaked:
        matrix.add(check_id(app, notebook.name, "noleak"), "FAIL", "%d kernel process(es) of this notebook survived the run (killed now): %s" % (len(leaked), leaked), notebook.name)
    else:
        matrix.add(check_id(app, notebook.name, "noleak"), "PASS", "no kernel process of this notebook is left", notebook.name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in ("app", "prefix", "src", "tag", "results", "lc-home"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--only", default="", help="comma list of notebook names (default: all)")
    args = parser.parse_args(argv)
    src = Path(args.src)
    notebooks = discover(src)
    if args.only:
        wanted = set(args.only.split(","))
        unknown = wanted - {n.name for n in notebooks}
        if unknown:
            print("ERROR: --only names unknown notebook(s) %s; the source lists %s" % (sorted(unknown), [n.name for n in notebooks]), file=sys.stderr)
            return 2
        notebooks = [n for n in notebooks if n.name in wanted]
    matrix = Matrix(Path(args.results) / args.app, "nb", "notebook", args.app, expected=expected_ids(args.app, notebooks))
    try:
        source_checks(matrix, args.app, Path(args.prefix), src, args.tag, notebooks)
    except OSError as problem:
        matrix.add(check_id(args.app, "notebooks", "inventory"), "FAIL", "runner error: %s" % problem)
    for notebook in notebooks:
        print("== %s / %s" % (args.app, notebook.name), flush=True)
        try:
            run_one(args, matrix, notebook)
        except Exception as problem:  # a runner bug must not stop the other notebooks
            matrix.add(check_id(args.app, notebook.name, "runs"), "FAIL", "runner error: %s: %s" % (type(problem).__name__, problem), notebook.name)
    counts = matrix.finish()
    print("nb %s: %s" % (args.app, counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
