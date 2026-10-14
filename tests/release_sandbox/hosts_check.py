"""What an INSTALLED app declares about its hosts, checked with the app's own Python (it has the pinned Tools). Prints
`CHECK <id> PASS|FAIL <detail>` lines like sandbox_checks.py.

    python hosts_check.py entry    --app NAME --expect-hosts notebook,napari   (the app must be registered with exactly these)
    python hosts_check.py entry    --app NAME --no-tools                       (the app ships no tools: nothing may be registered)
    python hosts_check.py sentence --app NAME --host fiji                      (print the exact skip/log sentence; empty: none)

The workflow passes the sentence to the Fiji and QuPath drivers (README.md, "Driver contract") so that they can look for it.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

GUI_HOSTS = ("napari", "fiji", "qupath")
# every id a run must print (the workflow's guard, verdict.py and required_checks.json, expect the same ids); hosts_2_list_does_not_show_it
# is not required for an app without tools: without labconstrictor_tools there is no `list` to ask, and a NOTE says so
REQUIRED_ENTRY = (
    "hosts_1_registry_entry_declares_the_hosts",
    "hosts_2_reference_function_matches_the_matrix",
    "hosts_3_list_shows_the_declaration",
)
REQUIRED_NO_TOOLS = ("hosts_1_app_without_tools_registers_nothing",)
failed: list[str] = []
seen: list[str] = []


def rec(cid: str, ok: bool, detail: object = "") -> None:
    seen.append(cid)
    print(
        "CHECK %s %s %s" % (cid, "PASS" if ok else "FAIL", str(detail).replace("\n", " | ")[:600]), flush=True
    )
    if not ok:
        failed.append(cid)


def not_run(ids: tuple[str, ...], reason: str) -> None:
    """Every id of `ids` that has not printed yet fails: a check that did not run is red, never absent."""
    for cid in ids:
        if cid not in seen:
            rec(cid, False, "not run: %s" % reason)


def entry_path(app: str) -> Path:
    return Path(os.environ.get("LC_HOME") or (Path.home() / ".labconstrictor")) / "apps" / (app + ".json")


def read_entry(app: str) -> dict[str, Any] | None:
    path = entry_path(app)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def tools_list() -> str:
    done = subprocess.run(
        [sys.executable, "-m", "labconstrictor_tools", "list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return done.stdout


def check_no_tools(app: str) -> None:
    """The app ships no *_lc_tools module (allowed by expected_hosts.json): the install must not have registered anything."""
    rec(
        "hosts_1_app_without_tools_registers_nothing",
        read_entry(app) is None,
        "entry file %s %s" % (entry_path(app), "exists" if entry_path(app).exists() else "absent"),
    )
    try:
        import labconstrictor_tools  # noqa: F401
    except ImportError:
        print(
            "NOTE hosts_2_tools_not_installed: the app installs no labconstrictor-tools, so no command can list it",
            flush=True,
        )
        return
    rec("hosts_2_list_does_not_show_it", app not in tools_list(), "")


def check_entry(app: str, expected: list[str]) -> None:
    """The registry entry declares exactly the expected hosts, the reference function agrees per host, `list` shows it."""
    entry = read_entry(app)
    if entry is None:
        rec("hosts_1_registry_entry_declares_the_hosts", False, "no registry entry for %s" % app)
        not_run(REQUIRED_ENTRY, "no registry entry for %s" % app)
        return
    declared = entry.get("hosts")
    if declared is None:
        detail = "the entry has no hosts field: the installer did not pass hosts (an older installer), so every host would list the app"
    else:
        detail = "entry hosts=%s expected=%s" % (declared, expected)
    rec(
        "hosts_1_registry_entry_declares_the_hosts",
        isinstance(declared, list) and sorted(declared) == sorted(expected),
        detail,
    )
    try:
        from labconstrictor_tools import app_hosts
    except ImportError as problem:
        rec(
            "hosts_2_reference_function_matches_the_matrix",
            False,
            "this Tools has no app_hosts (older than app_hosts_v1): %s" % problem,
        )
        not_run(REQUIRED_ENTRY, "this Tools has no app_hosts (older than app_hosts_v1)")
        return
    wrong = []
    for host in GUI_HOSTS:
        listed, sentence = app_hosts.listed_for(entry, host)
        if listed != (host in expected):
            wrong.append("%s: listed=%s sentence=%r" % (host, listed, sentence))
    rec(
        "hosts_2_reference_function_matches_the_matrix",
        not wrong,
        wrong or "napari, fiji and qupath as expected",
    )
    shown = tools_list()
    line = "hosts: %s" % app_hosts.declaration_text(entry)
    rec("hosts_3_list_shows_the_declaration", app in shown and line in shown, line)


def sentence(app: str, host: str) -> str:
    from labconstrictor_tools import app_hosts

    entry = read_entry(app)
    return "" if entry is None else app_hosts.listed_for(entry, host)[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["entry", "sentence"])
    parser.add_argument("--app", required=True)
    parser.add_argument("--expect-hosts", default="")
    parser.add_argument("--no-tools", action="store_true")
    parser.add_argument("--host", default="")
    args = parser.parse_args()
    if args.command == "sentence":
        print(sentence(args.app, args.host))
        return 0
    try:
        if args.no_tools:
            check_no_tools(args.app)
        else:
            check_entry(args.app, [h for h in args.expect_hosts.split(",") if h])
    except Exception as problem:  # noqa: BLE001  (named in a FAIL line, never swallowed)
        rec("hosts_0_check_crashed", False, "%s: %s" % (type(problem).__name__, problem))
    for cid in REQUIRED_NO_TOOLS if args.no_tools else REQUIRED_ENTRY:
        if cid not in seen:
            rec(cid, False, "printed no CHECK line")
    print("SECTION hosts: %d failed %s" % (len(failed), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
