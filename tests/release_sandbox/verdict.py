"""The fail-safe of the release sandbox: which expected CHECK lines never printed, and whether the job is red.

    python verdict.py guard   --checks all_checks.txt --os Linux|macOS|Windows --has-tools true|false
    python verdict.py verdict --checks all_checks.txt [--expected-fail ID,ID]

`guard` appends `CHECK missing_<id> FAIL expected CHECK line never printed` to the file for every id of required_checks.json
(for this system and this app variant) that has no CHECK line. `verdict` exits 1 when any `CHECK <id> FAIL` line is left,
except ids named in --expected-fail; every use of --expected-fail is printed as a NOTE. Exit codes: 0 ok, 1 red, 2 bad input.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NamedTuple

REQUIRED_FILE = Path(__file__).resolve().parent / "required_checks.json"
SYSTEMS = ("Linux", "macOS", "Windows")


class Verdict(NamedTuple):
    failed: list[str]  # every id with a FAIL line
    unexpected: list[str]  # failed and not in expected_fail: these make the job red
    expected: list[str]  # failed and in expected_fail
    not_failing: list[str]  # in expected_fail but without a FAIL line (a stale expectation)
    no_checks: bool  # no CHECK line at all

    @property
    def exit_code(self) -> int:
        return 1 if self.unexpected or self.no_checks else 0


def parse_checks(text: str) -> dict[str, bool]:
    """Id -> passed, from the `CHECK <id> PASS|FAIL <detail>` lines. An id with both a PASS and a FAIL line is failed."""
    found: dict[str, bool] = {}
    for line in text.splitlines():
        words = line.split(None, 3)
        if len(words) >= 3 and words[0] == "CHECK" and words[2] in ("PASS", "FAIL"):
            found[words[1]] = found.get(words[1], True) and words[2] == "PASS"
    return found


def parse_ids(text: str) -> list[str]:
    """A comma separated list of ids (spaces and empty items ignored)."""
    return [i.strip() for i in text.split(",") if i.strip()]


def required_ids(spec: dict[str, Any], has_tools: bool, system: str) -> list[str]:
    """The ids this system and app variant must print: the lists of every section that apply, in file order, no repeats."""
    if system not in SYSTEMS:
        raise ValueError("unknown system %r (one of %s)" % (system, ", ".join(SYSTEMS)))
    windows = system == "Windows"
    keys = ["all", "tools" if has_tools else "no_tools", "windows" if windows else "unix"]
    if windows and has_tools:
        keys.append("windows_tools")
    ids: list[str] = []
    for section in spec["sections"].values():
        for key in keys:
            ids += [i for i in section.get(key, []) if i not in ids]
    return ids


def missing_ids(text: str, required: list[str]) -> list[str]:
    seen = parse_checks(text)
    return [i for i in required if i not in seen]


def missing_lines(missing: list[str]) -> list[str]:
    return ["CHECK missing_%s FAIL expected CHECK line never printed" % i for i in missing]


def evaluate(text: str, expected_fail: list[str]) -> Verdict:
    seen = parse_checks(text)
    failed = sorted(i for i, passed in seen.items() if not passed)
    return Verdict(
        failed=failed,
        unexpected=[i for i in failed if i not in expected_fail],
        expected=[i for i in failed if i in expected_fail],
        not_failing=[i for i in expected_fail if i not in failed],
        no_checks=not seen,
    )


def load_spec(path: Path = REQUIRED_FILE) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("required_checks") != 1 or not isinstance(spec.get("sections"), dict):
        raise ValueError("%s is not a required_checks file of version 1" % path)
    return spec


def read_checks(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def run_guard(args: argparse.Namespace) -> int:
    if args.has_tools not in ("true", "false"):
        raise ValueError(
            "--has-tools must be true or false, got %r (the first step of the job did not set HAS_TOOLS)"
            % args.has_tools
        )
    required = required_ids(load_spec(), args.has_tools == "true", args.os)
    lines = missing_lines(missing_ids(read_checks(args.checks), required))
    with open(args.checks, "a", encoding="utf-8") as out:
        out.write("".join(line + "\n" for line in lines))
    print("guard: %d required ids, %d never printed" % (len(required), len(lines)))
    for line in lines:
        print(line)
    return 0


def run_verdict(args: argparse.Namespace) -> int:
    expected_fail = parse_ids(args.expected_fail)
    result = evaluate(read_checks(args.checks), expected_fail)
    if expected_fail:
        print(
            "NOTE expected_fail input is set: %s. These ids are allowed to be red in this run."
            % ", ".join(expected_fail)
        )
    for cid in result.expected:
        print("NOTE %s FAILED, as expected_fail says: not counted" % cid)
    for cid in result.not_failing:
        print("NOTE %s is in expected_fail but did not fail (stale expectation)" % cid)
    if result.no_checks:
        print("VERDICT RED: no CHECK line at all in %s" % args.checks)
    for cid in result.unexpected:
        print("VERDICT RED: CHECK %s FAIL" % cid)
    if not result.exit_code:
        print(
            "VERDICT GREEN: %d failed, all of them expected" % len(result.failed)
            if result.failed
            else "VERDICT GREEN: no FAIL line"
        )
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    guard = sub.add_parser("guard")
    guard.add_argument("--checks", required=True)
    guard.add_argument("--os", required=True)
    guard.add_argument("--has-tools", required=True)
    verdict = sub.add_parser("verdict")
    verdict.add_argument("--checks", required=True)
    verdict.add_argument("--expected-fail", default="")
    args = parser.parse_args(argv)
    try:
        return run_guard(args) if args.command == "guard" else run_verdict(args)
    except (OSError, ValueError) as problem:
        print("verdict.py: %s" % problem, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
