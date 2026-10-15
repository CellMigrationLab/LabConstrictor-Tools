#!/usr/bin/env python3
"""Run every case of a generated `cases.json` through `python -m labconstrictor_tools run` (the worker, no GUI) and save the reports.

GENERIC (standard library only):

    python run_cli_cases.py --app GuessTheCondition --data /home/user/synthetic/GuessTheCondition --reports /tmp/rep \\
        [--python PATH_TO_APP_PYTHON] [--scratch /tmp/work] [--only ID ...] [--timeout 600]

The dataset folder is COPIED to --scratch first (cases may write into fixtures, e.g. a game's results folder), the originals stay untouched.
Cases run in order (a game depends on its earlier steps). Writes `case_NN.json` for every case and `<dataset id>.json` for the primary
case of each dataset (what `check_ground_truth.py --reports` reads), and `cases_summary.json` that compares status, code and message of every
case with its own `expect` block. Environment (LC_HOME, PYTHONPATH, MPLBACKEND) is inherited.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def cli_params(inputs: dict[str, Any], base: Path) -> list[str]:
    """name=value arguments as the app's own sandbox builds them: booleans as true/false, a relative file that exists made absolute."""
    out = []
    for key, value in inputs.items():
        if isinstance(value, bool):
            value = "true" if value else "false"
        elif isinstance(value, str) and (base / value).exists():
            value = str((base / value).resolve())
        out.append("%s=%s" % (key, value))
    return out


def parse_report(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return {"status": "NOJSON", "error": text[-400:]}
    try:
        return json.loads(text[start : end + 1])
    except ValueError:
        return {"status": "NOJSON", "error": text[-400:]}


def judge(case: dict[str, Any], report: dict[str, Any]) -> list[str]:
    """Problems of a report against the case's own expectation (status, code, message): the cheap part of `labconstrictor-tools test`."""
    expect = case.get("expect", {})
    want = expect.get("status", "COMPLETE")
    problems = []
    if report.get("status") != want:
        problems.append(
            "status %s, expected %s: %s" % (report.get("status"), want, (report.get("error") or "")[:200])
        )
    elif want == "FAILED":
        if "code" in expect and report.get("code") != expect["code"]:
            problems.append("code %r, expected %r" % (report.get("code"), expect["code"]))
        if "message_contains" in expect and expect["message_contains"] not in (report.get("error") or ""):
            problems.append(
                "message %r lacks %r" % ((report.get("error") or "")[:200], expect["message_contains"])
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--app", required=True)
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="the generated dataset folder of the app (cases.json, fixtures, ground_truth.json)",
    )
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable, help="python of the app (default: this one)")
    parser.add_argument(
        "--scratch", type=Path, help="where to copy the dataset (default: a new temporary folder)"
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="run only the primary cases of these dataset ids (and nothing else)",
    )
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args(argv)

    scratch = args.scratch or Path(tempfile.mkdtemp(prefix="synthetic_run_"))
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(args.data, scratch)
    cases = json.loads((scratch / "cases.json").read_text(encoding="utf-8"))
    truth = json.loads((scratch / "ground_truth.json").read_text(encoding="utf-8"))
    primary = {d["primary_case"]: d["id"] for d in truth["datasets"] if d["primary_case"] is not None}
    wanted = {i for i, ident in primary.items() if ident in args.only} if args.only else None
    args.reports.mkdir(parents=True, exist_ok=True)
    summary = []
    for number, case in enumerate(cases):
        if wanted is not None and number not in wanted:
            continue
        job = scratch / "_jobs" / ("%03d" % number)
        job.parent.mkdir(exist_ok=True)
        command = [
            args.python,
            "-m",
            "labconstrictor_tools",
            "run",
            args.app,
            case["tool"],
            *cli_params(case.get("inputs", {}), scratch),
            "--out",
            str(job),
        ]
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout)
            report = parse_report(done.stdout)
            if report.get("status") == "NOJSON":
                report["error"] = (done.stderr or done.stdout)[-400:]
        except subprocess.TimeoutExpired:
            report = {"status": "TIMEOUT", "error": "no result after %g s" % args.timeout}
        text = json.dumps(report, indent=2)
        (args.reports / ("case_%03d.json" % number)).write_text(text, encoding="utf-8")
        if number in primary:
            (args.reports / (primary[number] + ".json")).write_text(text, encoding="utf-8")
        problems = judge(case, report)
        summary.append(
            {
                "case": number,
                "dataset": primary.get(number),
                "tool": case["tool"],
                "status": report.get("status"),
                "code": report.get("code"),
                "problems": problems,
                "comment": case.get("comment", "")[:90],
            }
        )
        print(
            "CASE %03d %-8s %-28s %s %s"
            % (
                number,
                report.get("status"),
                case["tool"],
                "OK" if not problems else "MISMATCH " + "; ".join(problems),
                case.get("comment", "")[:60],
            ),
            flush=True,
        )
    (args.reports / "cases_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    bad = [row for row in summary if row["problems"]]
    print("SUMMARY %d cases, %d differ from their own expectation" % (len(summary), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
