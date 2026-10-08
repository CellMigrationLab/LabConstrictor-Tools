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


# Characters that need no quoting for the Microsoft C runtime parser (and so for cmd.exe).
WINDOWS_SAFE = frozenset("-_.:/\\=+,")
BACKSLASH = "\\"
DOUBLE_QUOTE = '"'


def _quote_windows(text: str) -> str:
    """One argument for a Windows command line, by the documented rules of the C runtime / CommandLineToArgvW.

    Backslashes are literal, except that a run of them in front of a `"` is doubled (and the `"` escaped), and so is a run at
    the end of the text, which sits in front of the closing quote we add (`"C:\\My Data\\"` would otherwise swallow it).
    """
    if text and all(c.isalnum() or c in WINDOWS_SAFE for c in text):
        return text
    out = [DOUBLE_QUOTE]
    run = 0  # backslashes seen since the last other character
    for c in text:
        if c == BACKSLASH:
            run += 1
            continue
        out.append(BACKSLASH * (2 * run + 1) if c == DOUBLE_QUOTE else BACKSLASH * run)
        out.append(c)
        run = 0
    out.append(BACKSLASH * (2 * run) + DOUBLE_QUOTE)
    return "".join(out)


def quote(text: str, windows: bool | None = None) -> str:
    """Quote one argument for the shell of this machine (or of `windows`). The only place in the package that turns
    strings into shell text: a person pastes the result, so a name with a space or a quote must stay one argument.

    POSIX: `shlex.quote`. Windows: the C runtime rules (`_quote_windows`), for a line pasted into **cmd.exe** (PowerShell
    reads quotes by its own rules: use the Python snippet there). What cmd.exe does to the quoted text: `^ & | < >` are literal
    inside the quotes, so they need nothing; `%NAME%` is expanded by cmd.exe even inside quotes when NAME is a defined variable
    (not escapable without breaking the C runtime rules, so documented, see docs/HOST_FEATURES.md); every `"` flips cmd.exe's
    notion of "inside quotes", so a text with an odd number of `"` followed by an operator in a later argument is misread; a
    line break cannot be pasted at all. The expected outputs shared by every host are tests/quote_vectors.json.
    """
    windows = (os.name == "nt") if windows is None else windows
    return _quote_windows(text) if windows else shlex.quote(text)


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
    parts = [quote(x, windows) for x in parts]
    for p, value in _given(tool, values):
        parts.append(quote("%s=%s" % (p["name"], _text(value)), windows))
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
