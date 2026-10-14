"""Shared pieces of the notebook family (`nb`) of the one-off run: notebook discovery from the app's construct.yaml, id sanitising, the cell signature used by
the packaged check, and the environment every worker and kernel runs in (pinned kernelspec, scratch home, no package index).

Pure standard library plus PyYAML, so that the parent runner works with any Python 3.11 and the worker works in the app's own interpreter."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

WELCOME = "Welcome"
FAMILY = "nb"
CHECKS = ("packaged", "valid", "imports", "kernel", "runs", "oracle", "sideeffects", "noleak")


def sanitise(text: str) -> str:
    """An id fragment: every character outside [A-Za-z0-9_] becomes an underscore."""
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


def check_id(app: str, notebook: str, check: str) -> str:
    return "nb_%s_%s_%s" % (sanitise(app), sanitise(notebook), sanitise(check))


@dataclass(frozen=True)
class Notebook:
    """One packaged notebook: where it is in the source checkout and where the installer puts it (relative to the install prefix)."""

    name: str
    src_rel: str
    installed_rel: str


def discover(src: Path) -> list[Notebook]:
    """Every .ipynb of construct.yaml `extra_files` (source path -> installed path); raises ValueError when the file lists none."""
    construct = yaml.safe_load((src / "construct.yaml").read_text(encoding="utf-8"))
    found: list[Notebook] = []
    for entry in construct.get("extra_files", []):
        for source, destination in entry.items():
            if str(source).endswith(".ipynb"):
                found.append(Notebook(Path(str(source)).stem, str(source), str(destination)))
    if not found:
        raise ValueError("construct.yaml in %s lists no notebook in extra_files" % src)
    return found


def read_cells(path: Path) -> list[tuple[str, str]]:
    """(cell_type, source text) for every cell, whatever the way the file stores `source` (string or list of lines)."""
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    cells: list[tuple[str, str]] = []
    for cell in document["cells"]:
        source = cell.get("source", "")
        cells.append((str(cell["cell_type"]), "".join(source) if isinstance(source, list) else str(source)))
    return cells


def first_difference(installed: list[tuple[str, str]], released: list[tuple[str, str]]) -> str | None:
    """None when cell types and sources are equal, else a sentence naming the first differing cell."""
    for index in range(max(len(installed), len(released))):
        if index >= len(installed):
            return "cell %d is missing in the installed notebook (it has %d cells, the release %d)" % (index, len(installed), len(released))
        if index >= len(released):
            return "cell %d exists only in the installed notebook (it has %d cells, the release %d)" % (index, len(installed), len(released))
        if installed[index][0] != released[index][0]:
            return "cell %d type differs: installed %s, release %s" % (index, installed[index][0], released[index][0])
        if installed[index][1] != released[index][1]:
            return "cell %d source differs (installed %d chars, release %d chars)" % (index, len(installed[index][1]), len(released[index][1]))
    return None


def worker_env(prefix: Path, home: Path, lc_home: str, base: dict[str, str] | None = None) -> dict[str, str]:
    """The environment of the worker and of its kernel: HOME is a scratch folder, Jupyter finds only the app's kernelspec, pip has no index
    (a `%pip install` cannot download or change the app; the attempt is recorded by the audit hook)."""
    env = dict(os.environ if base is None else base)
    share = str(prefix / "share" / "jupyter")
    env.update(
        {
            "HOME": str(home),
            "JUPYTER_PATH": share,
            "JUPYTER_DATA_DIR": share,
            "JUPYTER_CONFIG_DIR": str(home / ".jupyter"),
            "JUPYTER_RUNTIME_DIR": str(home / "runtime"),
            "IPYTHONDIR": str(home / ".ipython"),
            "LC_HOME": lc_home,
            "PIP_NO_INDEX": "1",
            "PIP_CONFIG_FILE": os.devnull,
            "TMPDIR": str(home / "tmp"),
            "PYTHONNOUSERSITE": "1",
            "PYTHONUNBUFFERED": "1",
            "PATH": str(prefix / "bin") + os.pathsep + env.get("PATH", ""),
        }
    )
    env.pop("PYTHONPATH", None)
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    return env
