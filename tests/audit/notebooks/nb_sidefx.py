"""Side effects of a notebook run, recorded in the NOTE row `sideeffects`: files created in the app prefix, writes under the original home or the prefix seen by
the audit hook, network access (DNS, connections, HTTP status), subprocesses (pip!), and what the scratch home received.
"""

import json
import os
from pathlib import Path


def snapshot(root: Path, skip: tuple[str, ...] = ("__pycache__",)) -> dict[str, int]:
    """relative path -> size of every file under `root` (folders named in `skip` are only counted by the caller through `count_skipped`)."""
    found: dict[str, int] = {}
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            path = Path(folder, name)
            try:
                found[str(path.relative_to(root))] = path.stat().st_size
            except OSError:
                found[str(path.relative_to(root))] = -1
    return found


def diff(before: dict[str, int], after: dict[str, int]) -> tuple[list[str], list[str], list[str]]:
    """(created, changed, removed) relative paths."""
    created = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(p for p in set(before) & set(after) if before[p] != after[p])
    return created, changed, removed


def read_log(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"kind": "unreadable-log-line", "text": line[:100]})
    return events


def _short(names: list[str], limit: int = 8) -> str:
    return ", ".join(names[:limit]) + (" ... (+%d more)" % (len(names) - limit) if len(names) > limit else "")


def summarise(
    events: list[dict[str, str]],
    prefix_diff: tuple[list[str], list[str], list[str]],
    home_created: list[str],
    prefix: str,
) -> str:
    """One sentence per kind of side effect; 'none' says explicitly that nothing was seen."""
    parts = []
    created, changed, removed = prefix_diff
    parts.append(
        "app folder %s: created %s; changed %s; removed %s"
        % (prefix, _short(created) or "none", _short(changed) or "none", _short(removed) or "none")
    )
    writes = sorted({e["path"] for e in events if e["kind"] == "write"})
    pyc = [w for w in writes if "__pycache__" in w]
    other = [w for w in writes if "__pycache__" not in w]
    parts.append(
        "writes under the prefix or the original home seen by the audit hook: %s%s"
        % (_short(other) or "none", " (+%d .pyc)" % len(pyc) if pyc else "")
    )
    http = [e for e in events if e["kind"] == "http"]
    hosts = sorted({e.get("host", "") for e in events if e["kind"] == "dns"})
    parts.append(
        "network: %s; HTTP %s"
        % (
            "DNS " + _short(hosts) if hosts else "no lookups",
            "; ".join(
                "%s %s -> %s" % (e["method"], e["url"][:90], e.get("status", e.get("error")))
                for e in http[:6]
            )
            or "none",
        )
    )
    pops = [e["argv"] for e in events if e["kind"] in ("popen", "os.system", "os.exec", "os.posix_spawn")]
    pip = [p for p in pops if "pip" in p]
    parts.append(
        "subprocesses: %d (%s)%s"
        % (
            len(pops),
            _short(sorted({p[:60] for p in pops}), 4) or "none",
            "; PIP INVOKED: " + _short(pip, 3) if pip else "",
        )
    )
    parts.append("scratch home received %d files (%s)" % (len(home_created), _short(home_created, 5)))
    return " | ".join(parts)
