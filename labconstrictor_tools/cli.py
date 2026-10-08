"""Command-line tools for authors and administrators (the same declarations also give batch use for free).

labconstrictor-tools list                          installed apps and their tools
labconstrictor-tools run APP TOOL name=value ...   run a tool without any GUI (see `run APP TOOL --help`)
labconstrictor-tools check --module M              validate a declaration module (cheap to import? bounds sane? ...)
labconstrictor-tools doctor                        diagnose the installation (interpreters, schemas, staleness)
labconstrictor-tools test --module M --cases F     run tools on samples and check the results (authors)
labconstrictor-tools logs | support-bundle         the shared log file; a zip to attach to a bug report
"""

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from . import log, registry
from .client import Task
from .command import quote
from .structures import AppSchema, ParamSchema, RegistryEntry, ToolSchema

HEAVY_MODULES = (
    "numpy",
    "pandas",
    "scipy",
    "skimage",
    "torch",
    "tensorflow",
    "matplotlib",
    "cellpose",
    "numba",
)


# ---------------------------------------------------------------- list
def cmd_list(args: argparse.Namespace) -> int:
    schemas, problems = registry.load_schemas()
    if args.json:
        print(json.dumps({"apps": schemas, "problems": problems}, indent=2))
        return 0
    for name, schema in sorted(schemas.items()):
        print("%s  (%s)" % (name, schema.get("version") or "no version"))
        for tool in schema["tools"]:
            print("    %-24s %s" % (tool["id"], tool["label"]))
    for name, reason in problems:
        print("%s  -- skipped: %s" % (name, reason))
    return 0


# ---------------------------------------------------------------- run
def _find_tool(schema: AppSchema, wanted: str) -> ToolSchema:
    for tool in schema["tools"]:
        if wanted in (tool["id"], tool["label"]):
            return tool
    raise SystemExit("no such tool %r; available: %s" % (wanted, ", ".join(t["id"] for t in schema["tools"])))


def usage(app: str, tool: ToolSchema) -> str:
    lines = [
        "%s %s: %s" % (app, tool["id"], tool.get("description", tool["label"])),
        "  parameters (name=value):",
    ]
    for p in tool["inputs"]:
        detail = p["type"] + (" " + str(p["choices"]) if p.get("choices") else "")
        default = "required" if p["required"] else "default %r" % (p.get("default"),)
        bounds = (
            " [%s..%s]" % (p.get("minimum", ""), p.get("maximum", ""))
            if "minimum" in p or "maximum" in p
            else ""
        )
        lines.append(
            "    %-26s %s%s, %s%s"
            % (p["name"], detail, bounds, default, "  " + p["description"] if p.get("description") else "")
        )
    return "\n".join(lines)


def parse_value(param: ParamSchema, text: str) -> Any:
    kind = param["type"]
    try:
        if kind == "integer":
            return int(text)
        if kind == "float":
            return float(text)
    except ValueError:
        raise SystemExit("%s: expected a %s, got %r" % (param["name"], kind, text)) from None
    if kind == "boolean":
        if text.lower() not in ("1", "0", "true", "false", "yes", "no"):
            raise SystemExit("%s: expected true/false, got %r" % (param["name"], text))
        return text.lower() in ("1", "true", "yes")
    if (
        kind == "choice"
    ):  # the declared choice whose text matches (a choice may be a number); else as typed: the worker rejects it
        matches = [c for c in param.get("choices", []) if str(c) == text]
        return matches[0] if len(matches) == 1 else text
    return text  # image/labels/table/file: a path; string: as is


def cmd_run(args: argparse.Namespace) -> int:
    from . import client

    schemas, problems = registry.load_schemas()
    if args.app not in schemas:
        reason = dict(problems).get(args.app)
        if reason:
            raise SystemExit("app %r is installed but cannot be used: %s" % (args.app, reason))
        raise SystemExit("unknown app %r; installed: %s" % (args.app, ", ".join(sorted(schemas)) or "none"))
    tool = _find_tool(schemas[args.app], args.tool)
    if args.usage:
        print(usage(args.app, tool))
        return 0
    inputs = _parse_params(args.app, tool, args.params)
    if args.out:
        inputs["_job_dir"] = str(Path(args.out).resolve())
    else:  # a known place instead of a random /tmp folder per run; the newest RESULTS_KEPT runs are kept
        inputs["_job_dir"] = str(_new_results_dir(args.app, tool["id"]))
    started = time.time()
    try:
        task = client.run_once(
            args.app,
            tool["id"],
            inputs,
            on_update=_print_progress,
            timeout=args.timeout,
            record=not args.no_record,
        )
    except client.WorkerStartError as error:
        raise SystemExit("✖ %s" % error) from error
    except KeyboardInterrupt:  # Ctrl-C: the worker is closed by run_once's context manager; no traceback
        print("✖ interrupted; the worker was asked to stop", file=sys.stderr)
        return EXIT_INTERRUPTED
    if task.status != "COMPLETE" and not args.out:
        _remove_empty_job_dir(inputs["_job_dir"])
    print(json.dumps(_run_report(task, round(time.time() - started, 2)), indent=2))
    if task.status == "COMPLETE" and not args.out:
        print(
            "(results are in %s - use --out DIR to choose where they go; the newest %d runs are kept)"
            % (task.outputs["job_dir"], RESULTS_KEPT),
            file=sys.stderr,
        )
    return 0 if task.status == "COMPLETE" else 1


def _parse_params(app: str, tool: ToolSchema, pairs: Iterable[str]) -> dict[str, Any]:
    """`name=value` arguments -> typed inputs; a bad, unknown or repeated name exits with the usage."""
    by_name = {p["name"]: p for p in tool["inputs"]}
    inputs: dict[str, Any] = {}
    for pair in pairs:
        name, sep, text = pair.partition("=")
        if not sep or name not in by_name:
            raise SystemExit("bad parameter %r\n%s" % (pair, usage(app, tool)))
        if name in inputs:
            raise SystemExit("parameter %r was given more than once" % name)
        inputs[name] = parse_value(by_name[name], text)
    return inputs


def _remove_empty_job_dir(job_dir: str) -> None:
    try:
        Path(job_dir).rmdir()  # only if it is empty: nothing was produced, nothing to keep
    except OSError as error:  # not empty (or already gone): leave the folder, say so in the log
        log.logger().debug("job folder %s was not removed: %s: %s", job_dir, type(error).__name__, error)


def _run_report(task: Task, seconds: float) -> dict[str, Any]:
    """The JSON a finished `run` prints; a traceback of a failed task goes to stderr."""
    report: dict[str, Any] = {"status": task.status, "seconds": seconds}
    if task.record_dir:
        report["run_record"] = str(task.record_dir / "run.json")
    if task.status == "COMPLETE":
        report["results"] = task.outputs["results"]
        report["job_dir"] = task.outputs["job_dir"]
    else:
        report.update(error=task.error, code=task.code, log=str(log.log_path()))
        if task.traceback:
            print(task.traceback, file=sys.stderr)
    return report


RESULTS_KEPT = 20  # result folders of `run` that are kept; older ones are removed
RESULTS_DIR_ATTEMPTS = 20  # tries to find an unused results folder name before giving up
RESULTS_DIR_RANDOM_BYTES = 3  # random part of a results folder name (two runs in one second never collide)
LIVE_SCHEMA_TIMEOUT_S = 120  # doctor: how long an app's own interpreter gets to describe its tools
VERSION_PROBE_TIMEOUT_S = 20  # support bundle: how long `python -VV` of an app gets
BUNDLE_RUNS_KEPT = 10  # support bundle: the newest run records it includes
SLOW_DECLARATIONS_S = 0.5  # check: warn when importing the declarations takes longer than this
EXIT_INTERRUPTED = 130  # shell convention for Ctrl-C: 128 + SIGINT


_RUN_FOLDER = re.compile(
    r"^\d{8}T\d{6}_"
)  # what _new_results_dir creates: nothing else in results/ is ever pruned


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).lstrip(".") or "x"


def _new_results_dir(app: str, tool_id: str) -> Path:
    """<LC_HOME>/results/<time>_<id>_<app>_<tool>, created here (two runs in the same second never share a folder).
    Older run folders beyond RESULTS_KEPT are removed; only folders this command created (by name) are ever touched.
    """
    base = registry.home() / "results"
    base.mkdir(parents=True, exist_ok=True)
    folders = sorted(
        p for p in base.iterdir() if p.is_dir() and not p.is_symlink() and _RUN_FOLDER.match(p.name)
    )
    for old in folders[: max(0, len(folders) - (RESULTS_KEPT - 1))]:
        try:
            shutil.rmtree(old)
        except OSError as error:
            log.warning(
                "could not remove the old results folder %s (%s: %s)", old, type(error).__name__, error
            )
    for _ in range(RESULTS_DIR_ATTEMPTS):
        name = "%s_%s_%s_%s" % (
            time.strftime("%Y%m%dT%H%M%S"),
            os.urandom(RESULTS_DIR_RANDOM_BYTES).hex(),
            _slug(app),
            _slug(tool_id),
        )
        folder = base / name
        try:
            folder.mkdir()
        except FileExistsError:
            continue
        if folder.resolve().parent != base.resolve():
            raise SystemExit("refusing to write results outside %s: %s" % (base, folder))
        return folder
    raise SystemExit("could not create a results folder in %s" % base)


def _print_progress(message: str, fraction: float | None) -> None:
    shown = (
        "[ ?%]" if fraction is None else "[%3d%%]" % round(100 * fraction)
    )  # None = indeterminate, not 0 %
    print("%s %s" % (shown, message), file=sys.stderr)


# ---------------------------------------------------------------- check (for authors)
def _hints(item: Mapping[str, Any]) -> str:
    """The interaction hints of a parameter or output, so an author sees what hosts will do with it."""
    found: list[str] = []
    if item.get("choices_from"):
        found.append("dropdown from %s" % item["choices_from"]["tool"])
    if item.get("clear_after_run"):
        found.append("cleared after a run")
    if item.get("group_collapsed"):
        found.append("folded group")
    if item.get("widget"):
        found.append("shown as a %s" % item["widget"])
    if item.get("region_of"):
        found.append("filled from the selection on %s" % item["region_of"])
    if item.get("pick_channel"):
        found.append("channel chosen in the host")
    if item.get("replace"):
        found.append("replaces the previous result")
    if item.get("advanced"):
        found.append("advanced")
    return "   [%s]" % ", ".join(found) if found else ""


def cmd_check(args: argparse.Namespace) -> int:
    from .decorators import tools_in
    from .introspection import DeclarationError, describe_tools

    for path in args.pythonpath:
        sys.path.insert(0, path)
    before = set(sys.modules)
    started = time.perf_counter()
    try:
        importlib.import_module(args.module)
        schema = describe_tools(args.module)
    except DeclarationError as error:
        print("✖ invalid declaration: %s" % error)
        return 1
    seconds = time.perf_counter() - started
    heavy = sorted({m.split(".")[0] for m in set(sys.modules) - before} & set(HEAVY_MODULES))
    if not schema["tools"]:
        print("✖ module %s declares no tools (is the @tool decorator applied?)" % args.module)
        return 1
    for tool in schema["tools"]:
        print("✔ %-22s %s" % (tool["id"], tool["label"]))
        for p in tool["inputs"]:
            print(
                "      in  %-24s %-8s %s%s"
                % (
                    p["name"],
                    p["type"],
                    "required" if p["required"] else "default %r" % (p.get("default"),),
                    _hints(p),
                )
            )
        for o in tool["outputs"]:
            print("      out %-24s %-8s%s" % (o["name"], o["type"], _hints(o)))
    print("%d tool(s); declarations load in %.0f ms" % (len(tools_in(args.module)), seconds * 1000))
    if heavy:
        print(
            "⚠ importing this module also imported %s - move those imports inside the tool functions so that"
            % ", ".join(heavy)
        )
        print(
            "  registering and browsing tools stays instant (hosts only need the declarations until Run is pressed)"
        )
    if seconds > SLOW_DECLARATIONS_S:
        print("⚠ loading the declarations took %.1f s" % seconds)
    return 0


# ---------------------------------------------------------------- test (for authors)
def cmd_test(args: argparse.Namespace) -> int:
    from . import testing

    samples = {}
    for pair in args.sample:
        name, sep, path = pair.partition("=")
        if not sep:
            raise SystemExit("--sample expects name=path, got %r" % pair)
        if name in samples:
            raise SystemExit("--sample %r was given more than once" % name)
        samples[name] = str(Path(path).resolve())
    try:
        cases = testing.load_cases(args.cases) if args.cases else None
    except ValueError as error:  # an invalid cases file: say what is wrong, no traceback
        raise SystemExit("✖ %s" % error) from error
    reports, untested = testing.run_suite(
        args.module,
        args.pythonpath,
        cases,
        only=args.only,
        samples=samples,
        timeout=args.timeout,
        check_cancel=args.check_cancel,
        python=args.python,
    )
    if args.json:
        print(json.dumps({"reports": reports, "untested": untested}, indent=2))
    else:
        print(testing.format_report(reports, untested))
    return 1 if any(r["problems"] for r in reports) or not reports else 0


def cmd_export_notebook(args: argparse.Namespace) -> int:
    from . import exporter

    cells, errors = exporter.export_notebook(args.notebook, args.out)
    for cell in cells:
        for text in cell.warnings:
            print("⚠ %s: %s" % (cell.name, text))
    for text in errors:
        print("✖ %s" % text)
    if errors:
        return 1
    print("✔ %d tool(s) written to %s: %s" % (len(cells), args.out, ", ".join(c.name for c in cells)))
    return 0


# ---------------------------------------------------------------- doctor (for users and administrators)
def _live_schema(entry: RegistryEntry) -> tuple[subprocess.CompletedProcess[str], float]:
    env = {
        **os.environ,
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "PYTHONPATH": os.pathsep.join(x for x in (*entry["pythonpath"], entry["runtime_path"]) if x),
    }
    command = [entry["python"], "-m", "labconstrictor_tools", "describe", "--module", entry["module"]]
    started = time.perf_counter()
    result = subprocess.run(
        command, capture_output=True, text=True, env=env, encoding="utf-8", timeout=LIVE_SCHEMA_TIMEOUT_S
    )
    return result, time.perf_counter() - started


def _strip(schema: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in schema.items() if k not in ("application", "version")}


def diagnose() -> list[tuple[str, str, str]]:
    """-> list of (app, level, message); level in ok / warning / error."""
    entries, problems = registry.load_entries()
    findings = [(name, "error", reason) for name, reason in problems]
    for name, entry in sorted(entries.items()):
        findings.append(_diagnose_app(name, entry))
    if not entries and not problems:
        findings.append(
            ("-", "warning", "no apps registered in %s" % ", ".join(str(d) for d in registry.search_dirs()))
        )
    return findings


def _diagnose_app(name: str, entry: RegistryEntry) -> tuple[str, str, str]:
    """One registered app -> (app, level, message): is its cached schema what its own interpreter says now?"""
    try:
        cached = registry.schema(name)
    except ValueError as error:
        return (name, "error", str(error))
    try:
        result, seconds = _live_schema(entry)
        live = None if result.returncode else _strip(json.loads(result.stdout))
    except subprocess.TimeoutExpired:
        return (
            name,
            "error",
            "its interpreter did not answer within %d s (importing the tool module hangs?)"
            % LIVE_SCHEMA_TIMEOUT_S,
        )
    except (OSError, ValueError) as error:  # cannot start, or it printed something that is not a schema
        return (
            name,
            "error",
            "cannot load its tools with its own interpreter: %s: %s" % (type(error).__name__, error),
        )
    if result.returncode:
        lines = result.stderr.strip().splitlines()
        return (
            name,
            "error",
            "cannot load its tools with its own interpreter (exit %s): %s"
            % (result.returncode, lines[-1] if lines else "no error output"),
        )
    if live != _strip(cached):
        return (
            name,
            "warning",
            "cached schema is stale (the app changed): run `labconstrictor-tools register` again",
        )
    return (
        name,
        "ok",
        "%d tool(s), schema current, interpreter %s (%.2f s)"
        % (len(cached["tools"]), entry["python"], seconds),
    )


def cmd_doctor(args: argparse.Namespace) -> int:
    findings = diagnose()
    if args.json:
        print(json.dumps([{"app": a, "level": level, "message": m} for a, level, m in findings], indent=2))
    else:
        symbol = {"ok": "✔", "warning": "⚠", "error": "✖"}
        for app, level, message in findings:
            print("%s %-18s %s" % (symbol[level], app, message))
        print("registry search path: %s" % ", ".join(str(d) for d in registry.search_dirs()))
        print("log file: %s   (labconstrictor-tools logs | support-bundle)" % log.log_path())
    return 1 if any(level == "error" for _, level, _ in findings) else 0


# ---------------------------------------------------------------- logs and bug reports
def cmd_logs(args: argparse.Namespace) -> int:
    if args.path:
        print(log.log_path())
        return 0
    text = log.tail(args.lines)
    if not text:
        print("no log yet at %s (it is created the first time a tool or worker runs)" % log.log_path())
        return 0
    print(text, end="")
    return 0


def cmd_support_bundle(args: argparse.Namespace) -> int:
    """One zip with everything needed to debug a problem from afar: logs, registry entries, recent run records, versions."""
    import io
    import zipfile
    from contextlib import redirect_stdout
    from datetime import datetime

    out = Path(args.out or "labconstrictor-support-%s.zip" % datetime.now().strftime("%Y%m%d-%H%M%S"))
    home = registry.home()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as bundle:
        skipped: list[str] = []
        for folder, pattern in (("logs", "*.log*"), ("apps", "*.json")):
            for path in _bundle_files(home / folder, pattern, skipped):
                bundle.write(path, "%s/%s" % (folder, path.name))
        runs = sorted(p for p in (home / "runs").glob("*") if p.is_dir() and not p.is_symlink())
        for run in runs[-BUNDLE_RUNS_KEPT:]:
            for path in _bundle_files(run, "*.json", skipped):
                bundle.write(path, "runs/%s/%s" % (run.name, path.name))
        if skipped:
            bundle.writestr(
                "skipped.txt",
                "left out of this bundle (not regular files of the expected kind):\n" + "\n".join(skipped),
            )
            print(
                "⚠ left %d item(s) out of the bundle (symlinks or unexpected files): see skipped.txt in it"
                % len(skipped),
                file=sys.stderr,
            )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cmd_doctor(argparse.Namespace(json=False))
        bundle.writestr("doctor.txt", buffer.getvalue())
        bundle.writestr("environment.txt", _environment_report())
    print(
        "✔ wrote %s\n  Contains logs, app registrations, the last 10 run records (file paths and parameters, no image or table "
        "contents) and version information. Please attach it to the bug report." % out
    )
    return 0


def _bundle_files(folder: Path, pattern: str, skipped: list[str]) -> Iterator[Path]:
    """Regular files of the expected kind directly inside `folder`. A symlink would make the zip contain whatever it points
    to (a private key, say): leave those out and say so."""
    if not folder.is_dir() or folder.is_symlink():
        return
    for path in sorted(folder.glob("*")):
        expected = path.match(pattern)
        if (
            path.is_symlink()
            or not path.is_file()
            or not expected
            or path.resolve().parent != folder.resolve()
        ):
            if path.is_symlink() or path.is_file():
                skipped.append(str(path))
            continue
        yield path


def _environment_report() -> str:
    import platform
    from importlib import metadata

    lines = [log.environment_summary(), "", "installed packages in the host interpreter:"]
    lines += sorted(
        "  %s==%s" % (d.metadata["Name"], d.version) for d in metadata.distributions() if d.metadata["Name"]
    )
    entries, problems = registry.load_entries()
    lines += ["", "apps:"]
    for name, entry in sorted(entries.items()):
        try:
            result = subprocess.run(
                [entry["python"], "-VV"], capture_output=True, text=True, timeout=VERSION_PROBE_TIMEOUT_S
            )
            version = (result.stdout or result.stderr).strip()
        except (
            OSError,
            subprocess.SubprocessError,
        ) as error:  # cannot start, or timed out: the report says so
            log.warning(
                "environment report: %s -VV failed (%s: %s)", entry["python"], type(error).__name__, error
            )
            version = "cannot run: %s" % error
        lines.append("  %s %s: %s | %s" % (name, entry.get("version", ""), entry["python"], version))
    lines += ["  skipped: %s: %s" % p for p in problems]
    lines += [
        "",
        "platform: %s" % platform.platform(),
        "LC_APPS_PATH=%s" % os.environ.get("LC_APPS_PATH", ""),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- init (for app authors)
TEMPLATE = '''"""Tools of this app, declared as typed functions. Napari, Fiji and the notebook get their forms from these signatures.

Keep module-level imports light (only labconstrictor_tools and the standard library): import numpy / your science
package INSIDE the function so that registering and browsing tools stays instant.
"""

from typing import Annotated

from labconstrictor_tools import Image, ImageOut, Min, check_cancel, progress, tool


@tool("Gaussian blur")
def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
    """Smooth an image.

    Args:
        image: The image to smooth.
        sigma: Width of the Gaussian in pixels.
    """
    from skimage.filters import gaussian  # heavy import: inside the function

    progress(0.1, "smoothing")
    check_cancel()  # lets Cancel stop long loops cleanly
    return gaussian(image, sigma, preserve_range=True)
'''


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if target.exists():
        raise SystemExit("%s already exists; not overwriting" % target)
    target.write_text(TEMPLATE, encoding="utf-8")
    module = quote(target.stem)
    folder = quote(str(target.parent.resolve()))
    print(
        "wrote %s\nnext:\n  labconstrictor-tools check --module %s --pythonpath %s\n  labconstrictor-tools register --name myapp --prefix <app prefix> --module %s --pythonpath %s"
        % (target, module, folder, module, folder)
    )
    return 0
