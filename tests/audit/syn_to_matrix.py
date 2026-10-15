#!/usr/bin/env python3
"""Turn the output of check_ground_truth.py (CHECK/NOTE lines) into a matrix file (family synthetic).

usage: syn_to_matrix.py APP HOST CHECK_OUTPUT_TXT OUTDIR [REPORTS_DIR]

With REPORTS_DIR (a host run): a dataset whose case the form could not hold (not_expressible.json) or that the form refused before any run
('Run did not start a task; status: <warning>') is not a failure of the tool: its rows become NOTE rows that say so (not green, not red).
A report file that cannot be read becomes a FAIL row of its own, never a silent skip."""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from matrix import Matrix  # noqa: E402

CHECK = re.compile(r"^CHECK\s+(\S+)\s+(PASS|FAIL|NOT_RUN)\s*(.*)$")
NOTE = re.compile(r"^NOTE\s+(\S+)\s+(.*)$")
NOT_REPORTS = ("cases_summary.json", "not_expressible.json")


def special_datasets(reports: Path) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """({dataset id: why its failures are notes}, [(report file name, why it could not be read)])."""
    special: dict[str, str] = {}
    unreadable: list[tuple[str, str]] = []
    listing = reports / "not_expressible.json"
    if listing.is_file():
        for entry in json.loads(listing.read_text(encoding="utf-8")):
            if entry.get("dataset"):
                special[entry["dataset"]] = "the form cannot hold the value (%s)" % entry["why"][:150]
    for path in sorted(reports.glob("*.json")):
        if path.name.startswith("case_") or path.name in NOT_REPORTS:
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as problem:
            unreadable.append((path.name, str(problem)))
            continue
        error = str(document.get("error") or "")
        if document.get("status") == "DRIVER_ERROR" and "Run did not start a task; status:" in error:
            sentence = re.sub(r"\s+", " ", error.split("status:", 1)[1].split("|")[0]).strip()[:200]
            special[path.stem] = (
                "the form itself refused the input with a sentence before any run: %s" % sentence
            )
    return special, unreadable


def convert(matrix: Matrix, host: str, text: str, special: dict[str, str]) -> None:
    """Add one row per CHECK/NOTE line of `text` (the output of check_ground_truth.py)."""
    prefix = "syn_" if host == "cli" else "syn_host_%s_" % host
    dataset_ids = sorted(special, key=len, reverse=True)
    for line in text.splitlines():
        found = CHECK.match(line)
        if found:
            check_id, status, detail = found.groups()
            why = next((special[d] for d in dataset_ids if check_id.startswith(d + "_")), None)
            # a dataset id ending _cli is the CLI/worker expectation (no channel chooser); a host has one and picks a channel
            if host != "cli" and re.match(r"^\w+_cli_\d+_", check_id) and status != "PASS":
                why = "CLI-only expectation (worker without the host's channel chooser); the host picks a channel itself and ran the tool"
            tool = re.sub(r"_\d+_.*$", "", check_id)
            if why and status != "PASS":
                matrix.add(prefix + check_id, "NOTE", why, tool=tool)
            else:
                matrix.add(prefix + check_id, status, detail, tool=tool)
            continue
        found = NOTE.match(line)
        if found:
            name, detail = found.groups()
            status = "HUMAN" if "HUMAN" in detail or "judged by a person" in detail else "NOTE"
            matrix.add(prefix + name + "_note", status, detail, tool=name)


def main(argv: list[str]) -> int:
    if len(argv) not in (5, 6):
        print(__doc__, file=sys.stderr)
        return 2
    app, host, check_output, out = argv[1:5]
    special: dict[str, str] = {}
    unreadable: list[tuple[str, str]] = []
    if len(argv) == 6:
        special, unreadable = special_datasets(Path(argv[5]))
    matrix = Matrix(Path(out), "synthetic", host, app)
    for name, why in unreadable:
        matrix.add(
            "syn_unreadable_report_" + re.sub(r"\W", "_", name),
            "FAIL",
            "report %s cannot be read: %s" % (name, why),
        )
    convert(matrix, host, Path(check_output).read_text(encoding="utf-8", errors="replace"), special)
    print(matrix.finish())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
