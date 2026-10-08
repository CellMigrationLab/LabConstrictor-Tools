"""Copy as command: what a host puts on the clipboard so a form can be repeated outside it.

A terminal line (`labconstrictor_tools run <App> <tool> name=value ...`) and a Python snippet (`client.run_once`).
Images, labels and tables cannot be named by a layer or a window, so each gets a placeholder path and the text says so.
Parameters that are unset (None) are left out, exactly as the host leaves them out of the request.
Fiji and QuPath build the same text in Groovy (docs/HOST_FEATURES.md lists the format); this module is the reference.
"""

from __future__ import annotations

import os
import shlex
from typing import Any

FILE_TYPES = ("image", "labels", "table", "file", "folder")
PLACEHOLDER = {
    "image": "image.tif",
    "labels": "labels.tif",
    "table": "table.csv",
    "file": "file",
    "folder": "folder",
}


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _quote(text: str, windows: bool) -> str:
    if windows:
        if text and all(c.isalnum() or c in "-_.:/\\=+," for c in text):
            return text
        return '"' + text.replace('"', '\\"') + '"'
    return shlex.quote(text)


def _given(tool: dict, values: dict) -> list[tuple[dict, Any]]:
    """The inputs that are set, in the tool's order; file-like inputs without a path get their placeholder."""
    out = []
    for p in tool["inputs"]:
        value = values.get(p["name"])
        if value is None:
            if p["type"] in FILE_TYPES and p.get("required"):
                value = PLACEHOLDER[p["type"]]
            else:
                continue
        out.append((p, value))
    return out


def placeholders(tool: dict, values: dict) -> list[str]:
    """Names of the required file-like inputs that have no path in `values` (the person must fill these in)."""
    return [
        p["name"]
        for p in tool["inputs"]
        if p["type"] in FILE_TYPES and p.get("required") and values.get(p["name"]) is None
    ]


def command_line(
    app: str, tool: dict, values: dict, python: str = "python", windows: bool | None = None
) -> str:
    """`python -m labconstrictor_tools run App tool name=value ...`, quoted for the shell."""
    windows = (os.name == "nt") if windows is None else windows
    parts = [python, "-m", "labconstrictor_tools", "run", app, tool["id"]]
    parts = [_quote(x, windows) for x in parts]
    for p, value in _given(tool, values):
        parts.append(_quote("%s=%s" % (p["name"], _text(value)), windows))
    note = placeholders(tool, values)
    line = " ".join(parts)
    if note:
        line = "# replace the file for: %s\n%s" % (", ".join(note), line)
    return line


def python_snippet(app: str, tool: dict, values: dict) -> str:
    """Python that runs the tool once in its own environment's worker and prints the results."""
    given = _given(tool, values)
    body = "{\n" + "".join("    %r: %r,\n" % (p["name"], v) for p, v in given) + "}" if given else "{}"
    note = placeholders(tool, values)
    lines = []
    if note:
        lines.append("# replace the file for: %s" % ", ".join(note))
    lines += [
        "from labconstrictor_tools import client",
        "",
        "task = client.run_once(%r, %r, %s)" % (app, tool["id"], body),
        'print(task.status, task.outputs if task.status == "COMPLETE" else task.error)',
    ]
    return "\n".join(lines)
