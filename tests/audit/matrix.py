"""The result matrix of the audit (docs/TEST_STRATEGY.md section 0): one JSON file per family, host and app, rewritten atomically after
every row, so that a crash, a kill or an empty credit balance leaves everything done so far.

Rows: {id, family, host, app, tool, control, status, detail, seconds, screenshot, ts}. Statuses: PASS, FAIL, NOT_RUN (expected, not executed: red),
HUMAN (cannot be automated: listed for a person, never green), NOTE (information; counted on its own, never green).
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

STATUSES = ("PASS", "FAIL", "NOT_RUN", "HUMAN", "NOTE")
CHECK_LINE = re.compile(r"^(CHECK|NOTE)\s+(\S+)\s+(PASS|FAIL)?\s*(.*)$")


class Matrix:
    """One matrix file; `add` rewrites it atomically, `finish` marks every expected id without a row as NOT_RUN."""

    def __init__(
        self, directory: Path, family: str, host: str, app: str, expected: list[str] | None = None
    ) -> None:
        self.family, self.host, self.app = family, host, app
        self.path = directory / ("matrix_%s_%s_%s.json" % (family, host, app))
        self.expected = list(expected or [])
        self.rows: list[dict[str, Any]] = []
        self.started = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.finished: str | None = None
        directory.mkdir(parents=True, exist_ok=True)
        self._write()

    def add(
        self,
        check_id: str,
        status: str,
        detail: str = "",
        tool: str = "",
        control: str = "",
        seconds: float = 0.0,
        screenshot: str | None = None,
    ) -> None:
        if status not in STATUSES:
            raise ValueError("unknown status %r for %s" % (status, check_id))
        self.rows.append(
            {
                "id": check_id,
                "family": self.family,
                "host": self.host,
                "app": self.app,
                "tool": tool,
                "control": control,
                "status": status,
                "detail": detail.replace("\n", " | ")[:500],
                "seconds": round(seconds, 2),
                "screenshot": screenshot,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )
        self._write()

    def add_output(self, text: str, tool: str = "") -> int:
        """Rows from CHECK/NOTE lines of a driver's output (one line per assertion). Returns the number of rows added."""
        count = 0
        for line in text.splitlines():
            found = CHECK_LINE.match(line.strip())
            if not found:
                continue
            kind, check_id, verdict, detail = found.groups()
            if kind == "CHECK":
                if verdict is None:
                    self.add(
                        check_id, "FAIL", "malformed CHECK line (no PASS or FAIL): " + line.strip(), tool
                    )
                else:
                    self.add(check_id, verdict, detail, tool)
            else:
                self.add(check_id, "NOT_RUN" if "not run" in detail else "NOTE", detail, tool)
            count += 1
        return count

    def finish(self) -> dict[str, int]:
        """Mark expected ids without a row as NOT_RUN, stamp the end, and return the count per status."""
        seen = {row["id"] for row in self.rows}
        for check_id in self.expected:
            if check_id not in seen:
                self.add(check_id, "NOT_RUN", "expected, never executed")
        self.finished = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._write()
        return self.counts()

    def counts(self) -> dict[str, int]:
        return {status: sum(1 for row in self.rows if row["status"] == status) for status in STATUSES}

    def _write(self) -> None:
        document = {
            "host": self.host,
            "app": self.app,
            "family": self.family,
            "started": self.started,
            "finished": self.finished,
            "expected": len(self.expected),
            "rows": self.rows,
        }
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(document, indent=1), encoding="utf-8")
        os.replace(temporary, self.path)
