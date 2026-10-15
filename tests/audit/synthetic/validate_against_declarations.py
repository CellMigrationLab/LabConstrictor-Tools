#!/usr/bin/env python3
"""Check every generated case against the DECLARED inputs of the tool, from the app's source (no install, no heavy import).

    PYTHONPATH=<Tools repo> python validate_against_declarations.py SYN_DIR APP_SOURCES_DIR

The declaration modules (`src/<package>_lc_tools/__init__.py`) import only `labconstrictor_tools` at the top, so their schema can be read from the
source checkouts. For each case: the tool exists; every input name is declared; every required input is given (unless the case expects a refusal);
choices are valid, numbers lie within the declared range and files and folders exist (unless the case expects a refusal, which is how a value beyond
the limit or a missing file is tested on purpose). Exit 1 on any problem: a generated case that cannot be what it claims to be.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

APPS = {
    "NucleiSky": ("nucleisky_lc_tools", "NucleiSky"),
    "LabConstrictor-Playground": ("labconstrictor_playground_lc_tools", "LabConstrictor-Playground"),
    "LabConstrictor-VLab4Mic": ("vlab4mic_lc_tools", "LabConstrictor-VLab4Mic"),
    "GuessTheCondition": ("guessthecondition_lc_tools", "GuessTheCondition"),
    "CellTracksColab": ("celltracks_lc_tools", "CellTracksColab"),
}


def problems_of(case: dict, tools: dict, base: Path) -> list[str]:
    tool = tools.get(case["tool"])
    if tool is None:
        return ["no such tool %r" % case["tool"]]
    refusal = case.get("expect", {}).get("status") == "FAILED"
    params = {p["name"]: p for p in tool["inputs"]}
    out = []
    for name, value in case.get("inputs", {}).items():
        p = params.get(name)
        if p is None:
            out.append("input %r is not declared (declared: %s)" % (name, ", ".join(params)))
            continue
        if refusal:
            continue
        if "choices" in p and value not in p["choices"]:
            out.append("%s=%r is not one of %s" % (name, value, p["choices"]))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in p and value < p["minimum"] or "maximum" in p and value > p["maximum"]:
                out.append("%s=%r outside [%s, %s]" % (name, value, p.get("minimum"), p.get("maximum")))
        if (
            p["type"] in ("image", "labels", "table", "file", "folder")
            and isinstance(value, str)
            and not (base / value).exists()
        ):
            out.append("%s=%r does not exist" % (name, value))
    if not refusal:
        out += [
            "required input %r is missing" % p["name"]
            for p in tool["inputs"]
            if p["required"] and p["name"] not in case.get("inputs", {})
        ]
    return out


def check_app(app: str, root: Path, sources: Path) -> int:
    import importlib

    from labconstrictor_tools.introspection import describe_tools

    module, repo = APPS[app]
    sys.path.insert(0, str(sources / repo / "src"))
    importlib.import_module(module)
    tools = {t["id"]: t for t in describe_tools(module)["tools"]}
    cases = json.loads((root / app / "cases.json").read_text(encoding="utf-8"))
    found = [(i, p) for i, c in enumerate(cases) for p in problems_of(c, tools, root / app)]
    used = {c["tool"] for c in cases}
    no_case_file = root / app / "no_case.json"
    no_case = set(json.loads(no_case_file.read_text(encoding="utf-8"))) if no_case_file.exists() else set()
    uncovered = sorted(set(tools) - used - no_case)
    print(
        "%-28s %3d cases against %d declared tools: %d problem(s); tools with no case and no no_case.json entry: %s"
        % (app, len(cases), len(tools), len(found), uncovered or "none")
    )
    for i, p in found:
        print("  case %d (%s): %s" % (i, cases[i]["comment"][:50], p))
    return len(found) + len(uncovered)


def main(argv: list[str]) -> int:
    """One subprocess per app: the tool registry of Tools is global and refuses two apps that declare the same tool id (list_devices)."""
    import subprocess

    if len(argv) == 3:
        return 1 if check_app(argv[2], Path(argv[0]), Path(argv[1])) else 0
    bad = 0
    for app in APPS:
        done = subprocess.run(
            [sys.executable, __file__, argv[0], argv[1], app], capture_output=True, text=True
        )
        print(done.stdout + done.stderr, end="")
        bad += done.returncode
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
