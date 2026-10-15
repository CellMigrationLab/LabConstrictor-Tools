"""Turn every matrix file under a results directory into RESULTS.md: one table per app (family x host x status counts) and every FAIL, NOT_RUN and HUMAN
row with its detail.

    python collect_results.py RESULTS_DIR      (writes RESULTS_DIR/RESULTS.md and RESULTS_DIR/<round>/MATRICES.md)

Rounds are kept apart. A test round lives in its own folder `RESULTS_DIR/alphaN/` (alpha2, alpha3, alpha4, ...): its matrices are never mixed into the table of
another round. `RESULTS.md` holds the matrices that sit under no `alphaN` folder (the first round); every `alphaN` folder gets its own generated `MATRICES.md`
next to its hand-written RESULTS.md."""

import json
import re
import sys
from pathlib import Path
from typing import Any

STATUSES = ("PASS", "FAIL", "NOT_RUN", "HUMAN", "NOTE")
ROUND = re.compile(r"^alpha\d+$")
IGNORED_FOLDERS = ("audit_scratch",)  # the Napari synthetic driver's own recorder: no rows of its own
TITLE = "# Results of the test run"


def round_of(directory: Path, path: Path) -> str:
    """The round a matrix file belongs to: the first `alphaN` folder on its path below `directory`, or "" (the first round)."""
    return next((part for part in path.relative_to(directory).parts if ROUND.match(part)), "")


def rounds(directory: Path) -> list[str]:
    """Every round that has at least one matrix under `directory`, in numeric order (the first round, "", is not listed)."""
    found = {round_of(directory, p) for p in directory.rglob("matrix_*.json")} - {""}
    return sorted(found, key=lambda name: int(name[5:]))


def load(directory: Path, round_name: str = "") -> list[dict[str, Any]]:
    """The matrices of ONE round: `round_name` is "" for the matrices under no alphaN folder, else "alphaN". A file that cannot be read is listed with an `unreadable` reason."""
    documents: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("matrix_*.json")):
        if any(part in IGNORED_FOLDERS for part in path.relative_to(directory).parts):
            continue
        if round_of(directory, path) != round_name:
            continue
        try:
            documents.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as problem:
            documents.append(
                {"app": "?", "family": path.name, "host": "?", "rows": [], "unreadable": str(problem)}
            )
    return documents


def render(documents: list[dict[str, Any]], title: str = TITLE) -> str:
    lines = [title, ""]
    for app in sorted({str(d.get("app")) for d in documents}):
        lines += [
            "## " + app,
            "",
            "| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |",
            "|---|---|---|---|---|---|---|---|",
        ]
        mine = [d for d in documents if d.get("app") == app]
        for doc in mine:
            rows = doc.get("rows", [])
            count = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
            end = doc.get("finished") or "NOT FINISHED"
            if doc.get("unreadable"):
                end = "UNREADABLE: " + doc["unreadable"]
            lines.append(
                "| %s | %s | %d | %d | %d | %d | %d | %s |"
                % (
                    doc.get("family"),
                    doc.get("host"),
                    count["PASS"],
                    count["FAIL"],
                    count["NOT_RUN"],
                    count["HUMAN"],
                    count["NOTE"],
                    end,
                )
            )
        lines.append("")
        for status in ("FAIL", "NOT_RUN", "HUMAN"):
            hits = [(d, r) for d in mine for r in d.get("rows", []) if r["status"] == status]
            if hits:
                lines += ["### %s: %s (%d)" % (app, status, len(hits)), ""]
                for doc, row in hits:
                    lines.append(
                        "* `%s` (%s/%s) %s" % (row["id"], doc.get("family"), doc.get("host"), row["detail"])
                    )
                lines.append("")
    return "\n".join(lines) + "\n"


def collect(directory: Path) -> list[Path]:
    """Write RESULTS.md (the first round) and <round>/MATRICES.md for every round; returns the files written."""
    written = [directory / "RESULTS.md"]
    written[0].write_text(render(load(directory)), encoding="utf-8")
    for name in rounds(directory):
        target = directory / name / "MATRICES.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            render(load(directory, name), "# Results of the %s round (generated from the matrices)" % name),
            encoding="utf-8",
        )
        written.append(target)
    return written


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: collect_results.py RESULTS_DIR", file=sys.stderr)
        return 2
    for path in collect(Path(sys.argv[1])):
        print("wrote %s (%d bytes)" % (path, path.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
