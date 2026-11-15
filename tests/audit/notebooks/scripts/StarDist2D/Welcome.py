"""Click script of StarDist2D's Welcome.ipynb: the shared Welcome script (scripts/_welcome.py) plus the project version check.

Tester bug (1.1.1): the Welcome table said "The project version is outdated" (local 1.1.0, online 1.1.1) because the release did not update every version
field. The welcome stage is extended (here only, _welcome.py is unchanged): in the kernel, no table cell says "Project Outdated" and no widget or click output
(private-repository branch, where the table is loaded by the button) says "The project version is outdated". The oracle reads the executed notebook: the
Welcome cell's own outputs must not say it either, and the version the notebook reads from the installed construct.yaml must be the release's (construct.yaml
of the checkout at the tag); when GitHub was reachable and answered with another version, the line names both.
"""

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _welcome  # noqa: E402
from _stardist2d import construct_version, executed_cells, output_text  # noqa: E402

AFTER_CELL = _welcome.AFTER_CELL

OUTDATED = "The project version is outdated"
STAGES = {
    "welcome": _welcome.STAGES["welcome"] + """
_texts = [str(w.value) for w in lcnb.all_widgets() if type(w).__name__ in ("HTML", "HTMLMath", "Label")]
_click = globals().get("out")
if isinstance(_click, dict) and {"stdout", "outputs"} <= set(_click):  # private-repository branch: load_table ran inside the click (shared stage's `out`)
    _texts.append(json.dumps(_click["outputs"], default=str) + _click["stdout"])
_joined = " ".join(_texts)
lcnb.check("oracle_welcome_project_not_outdated", %r not in _joined and "Project Outdated" not in _joined,
           "table status cells %%s; widget/click text %%s" %% (status, ("says: " + _joined[_joined.find(%r):][:120]) if %r in _joined else "has no outdated message"))
""" % (OUTDATED, OUTDATED, OUTDATED),
}
NO_ORACLE = ""


def inputs(ctx: Any) -> dict[str, Any]:
    data = _welcome.inputs(ctx)
    data["version"] = construct_version(ctx)
    return data


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    expected = construct_version(ctx)
    path, cells = executed_cells(ctx, "app/menuinst/Welcome.ipynb")
    if cells is None:
        return [
            (
                "welcome_version_output",
                "FAIL",
                "the executed notebook %s does not exist: the Welcome outputs cannot be checked" % path,
            )
        ]
    text = "\n".join(output_text(o) for index, outputs in cells for o in outputs)
    rows: list[tuple[str, str, str]] = []
    outdated = re.search(
        r"The project version is outdated\. Local version: ([^,]*), Online version: (\S*)", text
    )
    rows.append(
        (
            "welcome_project_not_outdated_output",
            "FAIL" if outdated else "PASS",
            (
                ("the Welcome cell says: %s" % outdated.group(0))
                if outdated
                else "no 'project version is outdated' line in the Welcome cell outputs"
            ),
        )
    )
    local = outdated.group(1).strip() if outdated else None
    current = re.search(r"The project version is up-to-date\. Version: (\S+)", text)
    if current:
        local = current.group(1).strip()
    if local is None:
        rows.append(
            (
                "welcome_local_version",
                "NOTE",
                "no project version line in the Welcome cell outputs (the private-repository branch loads the table inside the button: checked in the kernel)",
            )
        )
    else:
        rows.append(
            (
                "welcome_local_version",
                "PASS" if local == expected else "FAIL",
                "the Welcome notebook reads the installed version %s; the release (construct.yaml at the tag) is %s"
                % (local, expected),
            )
        )
    return rows
