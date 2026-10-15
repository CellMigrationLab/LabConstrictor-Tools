"""Turn every matrix file under a results directory into RESULTS.md: one table per app (family x host x status counts) and every FAIL, NOT_RUN and HUMAN
row with its detail. Usage: python collect_results.py RESULTS_DIR (writes RESULTS_DIR/RESULTS.md)."""

import json
import sys
from pathlib import Path
from typing import Any


def load(directory: Path, rerun: "bool | str" = False) -> list[dict[str, Any]]:
    """The matrices under `directory`; a rerun lives in `directory/alphaN/` (alpha2, alpha3) and is kept apart from the alpha.1 round.
    `rerun=False` reads only the alpha.1 matrices (those under no alphaN folder), `rerun="alpha3"` reads only that round."""
    documents: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("matrix_*.json")):
        parts = path.relative_to(directory).parts
        if "audit_scratch" in parts:  # the Napari synthetic driver's own recorder (no rows of its own)
            continue
        folder = next((p for p in parts if p.startswith("alpha") and p[5:].isdigit()), "")
        if folder != (rerun or ""):
            continue
        try:
            documents.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as problem:
            documents.append({"app": "?", "family": path.name, "host": "?", "rows": [], "unreadable": str(problem)})
    return documents


def render(documents: list[dict[str, Any]]) -> str:
    lines = ["# Results of the one-off test run", ""]
    apps = sorted({str(d.get("app")) for d in documents})
    for app in apps:
        lines += ["## " + app, "", "| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |", "|---|---|---|---|---|---|---|---|"]
        mine = [d for d in documents if d.get("app") == app]
        for doc in mine:
            rows = doc.get("rows", [])
            count = {s: sum(1 for r in rows if r["status"] == s) for s in ("PASS", "FAIL", "NOT_RUN", "HUMAN", "NOTE")}
            end = doc.get("finished") or "NOT FINISHED"
            if doc.get("unreadable"):
                end = "UNREADABLE: " + doc["unreadable"]
            lines.append(
                "| %s | %s | %d | %d | %d | %d | %d | %s |"
                % (doc.get("family"), doc.get("host"), count["PASS"], count["FAIL"], count["NOT_RUN"], count["HUMAN"], count["NOTE"], end)
            )
        lines.append("")
        for status in ("FAIL", "NOT_RUN", "HUMAN"):
            hits = [(d, r) for d in mine for r in d.get("rows", []) if r["status"] == status]
            if hits:
                lines += ["### %s: %s (%d)" % (app, status, len(hits)), ""]
                for doc, row in hits:
                    lines.append("* `%s` (%s/%s) %s" % (row["id"], doc.get("family"), doc.get("host"), row["detail"]))
                lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: collect_results.py RESULTS_DIR", file=sys.stderr)
        return 2
    directory = Path(sys.argv[1])
    text = render(load(directory))
    (directory / "RESULTS.md").write_text(text, encoding="utf-8")
    print("wrote %s (%d bytes)" % (directory / "RESULTS.md", len(text)))
    for name in ("alpha2", "alpha3"):
        if (directory / name).is_dir():  # a rerun's generated tables go next to its hand-written RESULTS.md, never into the alpha.1 file
            again = render(load(directory, rerun=name)).replace("# Results of the one-off test run", "# Results of the %s rerun (generated from the matrices)" % name)
            (directory / name / "MATRICES.md").write_text(again, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
