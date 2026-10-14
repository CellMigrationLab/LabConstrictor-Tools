"""Tools that an app declares it has no case for: `lc_tests/no_case.json` next to the app's `cases.json`.

The file is optional: a JSON object `{tool_id: reason}` (reason = non-empty text). `4_every_tool_has_a_case` (sandbox_checks.py) fails for
a tool of the schema that has no case and is not named here, prints `NOTE 4_no_case_declared_<id>: <reason>` for each exemption, and
fails for a stale exemption (the tool has a case, or is not in the schema) and for a malformed file. An exemption is only honest if
something else runs the tool: `extras` (a step of the workflow) checks that the Playground extras (playground_extras.py) printed a
CHECK line for each exempt tool, or says in a NOTE that they were not run in this run.

    python no_case.py extras --cases CASES.json --extras playground|"" --checks checks_pg_tools.txt checks_pg_failures.txt
"""

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

FILE_NAME = "no_case.json"
# exempt tool -> the CHECK ids of playground_extras.py that run it (tests/test_release_sandbox_no_case.py keeps them real)
EXTRAS_CHECKS: dict[str, list[str]] = {
    "stress_real_memory": ["4_stress_real_memory"],
    "stress_hang": ["5c_killed_after_cancel_names_the_cancel"],
}
EXTRAS_ID = "4_no_case_tools_are_run_by_extras"


class Coverage(NamedTuple):
    unexplained: list[str]  # no case and not declared
    stale: list[str]  # declared, but it has a case or is not in the schema (each with its reason)
    problems: list[str]  # the file itself is malformed
    notes: list[str]  # one `NOTE 4_no_case_declared_<id>: <reason>` per valid exemption

    @property
    def ok(self) -> bool:
        return not (self.unexplained or self.stale or self.problems)

    def detail(self) -> str:
        return (
            "tools without a case and not declared in %s: %s | stale exemptions: %s | file problems: %s | declared: %d"
            % (
                FILE_NAME,
                self.unexplained,
                self.stale,
                self.problems,
                len(self.notes),
            )
        )


def load_declared(path: Path) -> tuple[dict[str, str], list[str]]:
    """The declared exemptions and the problems with the file. An absent file declares none (it is optional)."""
    if not path.exists():
        return {}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as problem:
        return {}, ["%s is not readable JSON: %s" % (FILE_NAME, problem)]
    if not isinstance(data, dict):
        return {}, ["%s must be a JSON object {tool_id: reason}, not %s" % (FILE_NAME, type(data).__name__)]
    problems = [
        "%s: the reason must be non-empty text, got %r" % (tool, why)
        for tool, why in data.items()
        if not isinstance(why, str) or not why.strip()
    ]
    return {tool: why for tool, why in data.items() if isinstance(why, str) and why.strip()}, problems


def coverage(
    all_ids: list[str], covered: set[str], declared: dict[str, str], problems: list[str]
) -> Coverage:
    stale = [
        "%s: %s" % (tool, "it has a case" if tool in covered else "it is not a tool of the schema")
        for tool in declared
        if tool in covered or tool not in all_ids
    ]
    return Coverage(
        unexplained=[i for i in all_ids if i not in covered and i not in declared],
        stale=stale,
        problems=problems,
        notes=[
            "NOTE 4_no_case_declared_%s: %s" % (tool, why)
            for tool, why in declared.items()
            if tool in all_ids and tool not in covered
        ],
    )


def extras_result(declared: dict[str, str], problems: list[str], extras_on: bool, checks_text: str) -> str:
    """The one line the extras step prints: a CHECK line, or (extras off, tools exempt) an explicit NOTE."""
    if problems:
        return "CHECK %s FAIL %s" % (EXTRAS_ID, "; ".join(problems))
    if not declared:
        return "CHECK %s PASS no tool is exempt from having a case" % EXTRAS_ID
    names = ", ".join(declared)
    if not extras_on:
        return (
            "NOTE %s: playground_extras is false, so the exempt tools (%s) were NOT run in this run: nothing here checked their behaviour"
            % (EXTRAS_ID, names)
        )
    lines = [ln.split() for ln in checks_text.splitlines() if ln.startswith("CHECK ")]
    printed = {words[1] for words in lines if len(words) > 1}
    missing = [
        "%s (%s)"
        % (
            tool,
            (
                "expected CHECK " + " or ".join(EXTRAS_CHECKS[tool])
                if tool in EXTRAS_CHECKS
                else "no extras check is known for it"
            ),
        )
        for tool in declared
        if not printed.intersection(EXTRAS_CHECKS.get(tool, []))
    ]
    if missing:
        return "CHECK %s FAIL the Playground extras printed no CHECK line for: %s" % (
            EXTRAS_ID,
            "; ".join(missing),
        )
    return "CHECK %s PASS every exempt tool was run by the Playground extras: %s" % (EXTRAS_ID, names)


def read_all(paths: list[str]) -> str:
    return "".join(Path(p).read_text(encoding="utf-8", errors="replace") for p in paths if Path(p).exists())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["extras"])
    parser.add_argument("--cases", required=True)
    parser.add_argument("--extras", default="")
    parser.add_argument("--checks", nargs="*", default=[])
    args = parser.parse_args(argv)
    declared, problems = load_declared(Path(args.cases).parent / FILE_NAME)
    print(extras_result(declared, problems, args.extras == "playground", read_all(args.checks)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
