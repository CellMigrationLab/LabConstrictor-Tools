"""Turn every matrix file under a results directory into RESULTS.md: one table per app (family x host x status counts) and every FAIL, NOT_RUN and HUMAN
row with its detail. Usage: python collect_results.py RESULTS_DIR (writes RESULTS_DIR/RESULTS.md)."""

import json
import sys
from pathlib import Path
from typing import Any


def load(directory: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("matrix_*.json")):
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
