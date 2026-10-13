"""Run records: what was run, with what, by which interpreter, and what came back - for support and reproducibility.

One folder per run under <LC_HOME>/runs/, carrying the owner and done markers of docs/SPEC_WRONG_SCIENCE.md section 3;
`retention.prune` keeps the newest 50 finished ones and never touches a folder it did not make. Everything stays on the local machine. A record holds
file *paths* and parameter values you passed, never image or table contents.

`record` is what the CLI and the Python client use: it makes the folder, writes everything and prunes. A host that makes its own
folder (owner marker when the run starts, so a crash leaves an owned, unfinished folder) and must never prune uses the pieces
instead: `build_record` (the content of `run.json`), `record_json` (its text) and `done_status` (the status for `.lc-done.json`),
then `retention.write_done`, then starts `labconstrictor-tools prune` itself (docs/PROTOCOL.md, "Result folders and run records").
"""

import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import log, registry, retention
from .protocol import JOB_DIR_KEY

STDERR_TAIL_CHARS = 4000
_DONE_STATUS = {"COMPLETE": "ok", "CANCELED": "cancelled"}  # every other task status is "failed"


def runs_dir() -> Path:
    return registry.home() / "runs"


def done_status(task_status: str, cancel_requested: bool = False) -> str:
    """The `.lc-done.json` status of a task that ended as `task_status` (docs/SPEC_WRONG_SCIENCE.md 3.2, decided 13 Oct).

    COMPLETE is ok, CANCELED is cancelled, FAILED is failed; a CRASHED task is cancelled when the person had pressed Cancel
    (`Task.cancel_requested`: the worker was killed because the tool did not stop) and failed otherwise. Any other status is failed.
    """
    if task_status == "CRASHED" and cancel_requested:
        return "cancelled"
    return _DONE_STATUS.get(task_status, "failed")


def build_record(
    app: str,
    tool_id: str,
    inputs: dict[str, Any],
    task: Any,
    seconds: float,
    stderr: str = "",
    *,
    run_id: str | None = None,
    started_utc: str | None = None,
    finished_utc: str | None = None,
) -> dict[str, Any]:
    """The content of `run.json` for one finished task, exactly what `record` writes; no folder, no marker, no pruning.

    `finished_utc` defaults to now (UTC, ISO-8601). A host that knows its own `run_id` and the time the run started passes them and
    gets `run_id` and `started_utc` in the record; without them the record has no such keys (the CLI's record is unchanged).
    It reads the registry for the app's version and writes nothing. Write the text with `record_json`.
    """
    entry: Mapping[str, Any] = registry.load_all().get(app) or {}
    return {
        **({"run_id": run_id} if run_id is not None else {}),
        "app": app,
        "app_version": entry.get("version"),
        "tool": tool_id,
        **({"started_utc": started_utc} if started_utc is not None else {}),
        "finished_utc": finished_utc or datetime.now(timezone.utc).isoformat(),
        "seconds": round(seconds, 2),
        "status": task.status,
        "error": task.error,
        "code": task.code,
        "traceback": task.traceback,
        "inputs": {
            k: v for k, v in inputs.items() if k != JOB_DIR_KEY
        },  # the host-owned folder is not a user input
        "results": [
            {k: v for k, v in r.items() if k != "matrix_yx"} for r in task.outputs.get("results", [])
        ],
        "timings": task.outputs.get("timings"),
        "interpreter": task.outputs.get("diagnostics"),
        "stderr_tail": stderr[-STDERR_TAIL_CHARS:],
    }


def record_json(content: Mapping[str, Any]) -> str:
    """The text of `run.json` for `content` (what `record` writes: indented, anything that is not JSON written as text)."""
    return json.dumps(content, indent=2, default=str)


def record(
    app: str, tool_id: str, inputs: dict[str, Any], task: Any, seconds: float, stderr: str = ""
) -> Path | None:
    """Write the record of one finished task; returns the record folder. Never raises (a log must not break a run)."""
    try:
        started = datetime.now(timezone.utc)
        folder = runs_dir() / ("%s_%s_%s" % (started.strftime("%Y%m%dT%H%M%S%f"), _safe(app), _safe(tool_id)))
        runs_dir().mkdir(parents=True, exist_ok=True)
        folder.mkdir()  # never an existing folder: it would be marked as ours
        retention.write_owner(folder, "run", "cli")
        content = build_record(app, tool_id, inputs, task, seconds, stderr, finished_utc=started.isoformat())
        (folder / "run.json").write_text(record_json(content), encoding="utf-8")
        retention.write_done(folder, done_status(task.status, getattr(task, "cancel_requested", False)))
        retention.prune("runs")
        return folder
    except (
        Exception  # noqa: BLE001 - a record must never break a run, but its absence must be visible
    ) as error:
        log.warning(
            "could not write the run record for %s %s: %s: %s", app, tool_id, type(error).__name__, error
        )
        return None


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
