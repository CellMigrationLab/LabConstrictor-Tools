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
import subprocess
import sys
import time
from pathlib import Path

from . import log, registry

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
def cmd_list(args):
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
def _find_tool(schema, wanted):
    for tool in schema["tools"]:
        if wanted in (tool["id"], tool["label"]):
            return tool
    raise SystemExit("no such tool %r; available: %s" % (wanted, ", ".join(t["id"] for t in schema["tools"])))


def usage(app, tool):
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


def parse_value(param, text):
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
    return text  # image/labels/table/file: a path; string/choice: as is (the worker validates choices)


def cmd_run(args):
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
    by_name = {p["name"]: p for p in tool["inputs"]}
    inputs = {}
    for pair in args.params:
        name, sep, text = pair.partition("=")
        if not sep or name not in by_name:
            raise SystemExit("bad parameter %r\n%s" % (pair, usage(args.app, tool)))
        inputs[name] = parse_value(by_name[name], text)
    if args.out:
        inputs["_job_dir"] = str(Path(args.out).resolve())
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
    report = {"status": task.status, "seconds": round(time.time() - started, 2)}
    if getattr(task, "record_dir", None):
        report["run_record"] = str(task.record_dir / "run.json")
    if task.status == "COMPLETE":
        report["results"] = task.outputs["results"]
        report["job_dir"] = task.outputs["job_dir"]
    else:
        report.update(error=task.error, code=task.code, log=str(log.log_path()))
        if task.traceback:
            print(task.traceback, file=sys.stderr)
    print(json.dumps(report, indent=2))
    if task.status == "COMPLETE" and not args.out and not args.keep:
        print(
            "(results are in %s - use --out DIR to choose where they go)" % task.outputs["job_dir"],
            file=sys.stderr,
        )
    return 0 if task.status == "COMPLETE" else 1


def _print_progress(message, fraction):
    print("[%3d%%] %s" % (100 * (fraction or 0), message), file=sys.stderr)


# ---------------------------------------------------------------- check (for authors)
def cmd_check(args):
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
                "      in  %-24s %-8s %s"
                % (p["name"], p["type"], "required" if p["required"] else "default %r" % (p.get("default"),))
            )
        for o in tool["outputs"]:
            print("      out %-24s %s" % (o["name"], o["type"]))
    print("%d tool(s); declarations load in %.0f ms" % (len(tools_in(args.module)), seconds * 1000))
    if heavy:
        print(
            "⚠ importing this module also imported %s - move those imports inside the tool functions so that"
            % ", ".join(heavy)
        )
        print(
            "  registering and browsing tools stays instant (hosts only need the declarations until Run is pressed)"
        )
    if seconds > 0.5:
        print("⚠ loading the declarations took %.1f s" % seconds)
    return 0


# ---------------------------------------------------------------- test (for authors)
def cmd_test(args):
    from . import testing

    samples = {}
    for pair in args.sample:
        name, sep, path = pair.partition("=")
        if not sep:
            raise SystemExit("--sample expects name=path, got %r" % pair)
        samples[name] = str(Path(path).resolve())
    cases = testing.load_cases(args.cases) if args.cases else None
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


def cmd_export_notebook(args):
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
def _live_schema(entry):
    env = {
        **os.environ,
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": os.pathsep.join([entry["runtime_path"], *entry["pythonpath"]]),
    }
    command = [entry["python"], "-m", "labconstrictor_tools", "describe", "--module", entry["module"]]
    started = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, env=env, encoding="utf-8", timeout=120)
    return result, time.perf_counter() - started


def _strip(schema):
    return {k: v for k, v in schema.items() if k not in ("application", "version")}


def diagnose():
    """-> list of (app, level, message); level in ok / warning / error."""
    entries, problems = registry.load_entries()
    findings = [(name, "error", reason) for name, reason in problems]
    for name, entry in sorted(entries.items()):
        try:
            cached = registry.schema(name)
        except ValueError as error:
            findings.append((name, "error", str(error)))
            continue
        result, seconds = _live_schema(entry)
        if result.returncode:
            findings.append(
                (
                    name,
                    "error",
                    "cannot load its tools with its own interpreter: "
                    + result.stderr.strip().splitlines()[-1],
                )
            )
        elif _strip(json.loads(result.stdout)) != _strip(cached):
            findings.append(
                (
                    name,
                    "warning",
                    "cached schema is stale (the app changed): run `labconstrictor-tools register` again",
                )
            )
        else:
            findings.append(
                (
                    name,
                    "ok",
                    "%d tool(s), schema current, interpreter %s (%.2f s)"
                    % (len(cached["tools"]), entry["python"], seconds),
                )
            )
    if not entries and not problems:
        findings.append(
            ("-", "warning", "no apps registered in %s" % ", ".join(str(d) for d in registry.search_dirs()))
        )
    return findings


def cmd_doctor(args):
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
def cmd_logs(args):
    if args.path:
        print(log.log_path())
        return 0
    text = log.tail(args.lines)
    if not text:
        print("no log yet at %s (it is created the first time a tool or worker runs)" % log.log_path())
        return 0
    print(text, end="")
    return 0


def cmd_support_bundle(args):
    """One zip with everything needed to debug a problem from afar: logs, registry entries, recent run records, versions."""
    import io
    import zipfile
    from contextlib import redirect_stdout
    from datetime import datetime

    out = Path(args.out or "labconstrictor-support-%s.zip" % datetime.now().strftime("%Y%m%d-%H%M%S"))
    home = registry.home()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as bundle:
        for folder in ("logs", "apps"):
            for path in sorted((home / folder).glob("*")) if (home / folder).is_dir() else []:
                if path.is_file():
                    bundle.write(path, "%s/%s" % (folder, path.name))
        runs = sorted(p for p in (home / "runs").glob("*") if p.is_dir()) if (home / "runs").is_dir() else []
        for run in runs[-10:]:
            for path in run.glob("*.json"):
                bundle.write(path, "runs/%s/%s" % (run.name, path.name))
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


def _environment_report():
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
            result = subprocess.run([entry["python"], "-VV"], capture_output=True, text=True, timeout=20)
            version = (result.stdout or result.stderr).strip()
        except Exception as error:  # noqa: BLE001
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


def cmd_init(args):
    target = Path(args.path)
    if target.exists():
        raise SystemExit("%s already exists; not overwriting" % target)
    target.write_text(TEMPLATE, encoding="utf-8")
    module = target.stem
    print(
        "wrote %s\nnext:\n  labconstrictor-tools check --module %s --pythonpath %s\n  labconstrictor-tools register --name myapp --prefix <app prefix> --module %s --pythonpath %s"
        % (target, module, target.parent.resolve(), module, target.parent.resolve())
    )
    return 0
