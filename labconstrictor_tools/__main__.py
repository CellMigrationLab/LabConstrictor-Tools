"""python -m labconstrictor_tools <command>   (also installed as the `labconstrictor-tools` command)

Used by installers : register | unregister
Used by hosts      : describe | serve                (internal: schema generation and the tool worker)
Used by people     : list | run | check | test | doctor     (see cli.py)
"""

import argparse
import errno
import importlib
import json
import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # the class is private in argparse: needed only to say what `sub` is
    Subparsers = argparse._SubParsersAction[argparse.ArgumentParser]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labconstrictor-tools", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    _add_describe_command(sub)
    _add_serve_command(sub)
    _add_register_command(sub)
    _add_unregister_command(sub)
    _add_list_command(sub)
    _add_run_command(sub)
    _add_check_command(sub)
    _add_test_command(sub)
    _add_export_command(sub)
    _add_init_command(sub)
    _add_logs_command(sub)
    _add_bundle_command(sub)
    _add_doctor_command(sub)
    return parser


def _add_describe_command(sub: "Subparsers") -> None:
    describe = sub.add_parser("describe", help="print the JSON schema of a declaration module (internal)")
    describe.add_argument("--module", required=True)
    describe.add_argument("--application")
    describe.add_argument("--version")


def _add_serve_command(sub: "Subparsers") -> None:
    serve = sub.add_parser("serve", help="run the tool worker on stdin/stdout (internal)")
    serve.add_argument("--module", required=True)
    serve.add_argument("--pythonpath", action="append", default=[])


def _add_register_command(sub: "Subparsers") -> None:
    register = sub.add_parser(
        "register", help="make an installed app visible to Napari/Fiji (post-install step)"
    )
    register.add_argument("--name", required=True)
    register.add_argument("--prefix", required=True, help="install prefix of the app (contains its python)")
    register.add_argument(
        "--module", required=True, help="module declaring the tools, importable in the app's Python"
    )
    register.add_argument("--version", default="")
    register.add_argument("--display-name")
    register.add_argument("--pythonpath", action="append", default=[])
    register.add_argument(
        "--dir", help="write the entry here instead of the per-user registry (e.g. a shared folder)"
    )


def _add_unregister_command(sub: "Subparsers") -> None:
    unregister = sub.add_parser("unregister", help="remove an app (pre-uninstall step)")
    unregister.add_argument("--name", required=True)
    unregister.add_argument("--dir")
    unregister.add_argument("--prefix", help="only remove the entry if it belongs to this install prefix")


def _add_list_command(sub: "Subparsers") -> None:
    lst = sub.add_parser("list", help="installed apps and their tools")
    lst.add_argument("--json", action="store_true")


def _add_run_command(sub: "Subparsers") -> None:
    run = sub.add_parser("run", help="run a tool without a GUI")
    run.add_argument("app")
    run.add_argument("tool")
    run.add_argument("params", nargs="*", metavar="name=value")
    run.add_argument("--usage", action="store_true", help="show the tool's parameters and exit")
    run.add_argument("--out", help="directory for the results (default: a temporary one)")
    run.add_argument(
        "--keep", action="store_true", help="(no effect, kept for compatibility: results are always kept)"
    )
    run.add_argument(
        "--no-record", action="store_true", help="do not write a run record under <LC_HOME>/runs"
    )
    run.add_argument("--timeout", type=float, default=None, help="kill the worker after this many seconds")


def _add_check_command(sub: "Subparsers") -> None:
    check = sub.add_parser("check", help="validate a declaration module (for app authors)")
    check.add_argument("--module", required=True)
    check.add_argument("--pythonpath", action="append", default=[])


def _add_test_command(sub: "Subparsers") -> None:
    test = sub.add_parser("test", help="run the tools on small samples and check the results (for authors)")
    test.add_argument("--module", required=True)
    test.add_argument("--pythonpath", action="append", default=[])
    test.add_argument("--python", help="interpreter for the workers (default: this one)")
    test.add_argument("--cases", help="JSON file with test cases; without it every tool gets a smoke test")
    test.add_argument("--sample", action="append", default=[], metavar="name=path")
    test.add_argument("--only", help="test just this tool id")
    test.add_argument("--timeout", type=float, default=120)
    test.add_argument("--check-cancel", action="store_true", help="also check that tools react to cancel")
    test.add_argument("--json", action="store_true")


def _add_export_command(sub: "Subparsers") -> None:
    export = sub.add_parser("export-notebook", help="write the %%%%lc_tool cells of a notebook to a module")
    export.add_argument("notebook")
    export.add_argument("--out", default="lc_tools.py")


def _add_init_command(sub: "Subparsers") -> None:
    init = sub.add_parser("init", help="write a starter declaration module (for app authors)")
    init.add_argument("path", help="e.g. my_app_tools.py")


def _add_logs_command(sub: "Subparsers") -> None:
    logs = sub.add_parser("logs", help="show the end of the log file (all front-ends write to it)")
    logs.add_argument("-n", "--lines", type=int, default=60)
    logs.add_argument("--path", action="store_true", help="print the log file location only")


def _add_bundle_command(sub: "Subparsers") -> None:
    bundle = sub.add_parser(
        "support-bundle", help="zip logs, registry and versions to attach to a bug report"
    )
    bundle.add_argument("--out")


def _add_doctor_command(sub: "Subparsers") -> None:
    doctor = sub.add_parser("doctor", help="diagnose the installation")
    doctor.add_argument("--json", action="store_true")


def _tolerant_streams() -> None:
    """Windows consoles/pipes often use cp1252/cp437: printing the status symbols (check, cross, warning) must never crash a command."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (
            AttributeError,
            ValueError,
        ) as error:  # a stream without reconfigure (replaced by a host/test): keep it as it is
            logging.getLogger("labconstrictor").debug(
                "cannot make %r tolerant of encoding errors: %s", stream, error
            )


def _reader_went_away(error: OSError) -> bool:
    """A write to a closed pipe: EPIPE everywhere, but Windows reports EINVAL for it."""
    return isinstance(error, BrokenPipeError) or (os.name == "nt" and error.errno == errno.EINVAL)


def main(argv: list[str] | None = None) -> int:
    try:
        code = _main(argv)
        sys.stdout.flush()  # buffered output that nobody reads fails here, where it is handled, not at interpreter exit
        return code
    except OSError as error:
        if not _reader_went_away(error):
            raise
        # whoever reads our output (`| head`, a pager that was quit) went away: that is not an error worth a traceback.
        # stdout is pointed at the null device so that the flush at interpreter exit cannot fail a second time.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError, AttributeError) as error:  # best effort; the exit code stays 0
            logging.getLogger("labconstrictor").debug(
                "cannot redirect stdout after a broken pipe: %s: %s", type(error).__name__, error
            )
        return 0


def _main(argv: list[str] | None = None) -> int:
    _tolerant_streams()
    args = build_parser().parse_args(argv)
    if args.command == "describe":
        from contextlib import redirect_stdout

        from .introspection import describe_tools

        # stdout is a machine protocol here (the registry stores it as the schema): whatever the declaration module prints
        # while it is imported goes to stderr, so the JSON document is the only thing on stdout
        with redirect_stdout(sys.stderr):
            importlib.import_module(args.module)
            schema = describe_tools(args.module, args.application, args.version)
        print(json.dumps(schema, indent=2))
    elif args.command == "serve":
        from .worker import Worker

        Worker(args.module, args.pythonpath).serve()
    elif args.command == "register":
        from . import registry

        entry = registry.register(
            args.name, args.prefix, args.module, args.version, args.pythonpath, args.display_name, args.dir
        )
        print(json.dumps(entry, indent=2))
    elif args.command == "unregister":
        from . import registry

        print(registry.unregister(args.name, args.dir, args.prefix))
    else:
        from . import cli

        return {
            "list": cli.cmd_list,
            "run": cli.cmd_run,
            "check": cli.cmd_check,
            "test": cli.cmd_test,
            "logs": cli.cmd_logs,
            "support-bundle": cli.cmd_support_bundle,
            "export-notebook": cli.cmd_export_notebook,
            "doctor": cli.cmd_doctor,
            "init": cli.cmd_init,
        }[args.command](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
