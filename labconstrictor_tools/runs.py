"""Run records: what was run, with what, by which interpreter, and what came back - for support and reproducibility.

One folder per run under <LC_HOME>/runs/, newest kept (default 50). Everything stays on the local machine. A record holds
file *paths* and parameter values you passed, never image or table contents.
"""

import json
import re
import shutil
from datetime import datetime, timezone

from . import registry
from .protocol import JOB_DIR_KEY

KEEP = 50
STDERR_TAIL_CHARS = 4000


def runs_dir():
    return registry.home() / "runs"


def record(app, tool_id, inputs, task, seconds, stderr=""):
    """Write the record of one finished task; returns the record folder. Never raises (a log must not break a run)."""
    try:
        started = datetime.now(timezone.utc)
        folder = runs_dir() / ("%s_%s_%s" % (started.strftime("%Y%m%dT%H%M%S%f"), _safe(app), _safe(tool_id)))
        folder.mkdir(parents=True, exist_ok=True)
        entry = registry.load_all().get(app, {})
        content = {
            "app": app,
            "app_version": entry.get("version"),
            "tool": tool_id,
            "finished_utc": started.isoformat(),
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
        (folder / "run.json").write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
        _prune()
        return folder
    except Exception:  # noqa: BLE001
        return None


def _safe(text):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def _prune(keep=KEEP):
    folders = sorted(p for p in runs_dir().iterdir() if p.is_dir())
    for old in folders[:-keep]:
        shutil.rmtree(old, ignore_errors=True)
