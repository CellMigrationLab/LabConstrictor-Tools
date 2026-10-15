"""Click script shared by the Welcome.ipynb of every app (the notebook is generated from one template: a table of the app's notebooks with an "Open the notebook"
button each, a version check against the GitHub API, and, when GitHub does not answer 200, a form for a personal access token).

The stage runs after the table cell: it reaches the table (through the "Load Private GitHub Repo" button when the form is shown), asserts that every notebook that
construct.yaml ships has a row and an open button, clicks every open button and asserts the JavaScript it displays targets the right notebook path, and clicks the
"Update" buttons (they write only into the scratch copy of the app folder). The "Update Source Code" button runs `pip install .. --force-reinstall` in the app's own
environment and is never clicked: HUMAN."""

import json
from pathlib import Path
from typing import Any

import yaml

AFTER_CELL = {1: "welcome"}
STAGES = {
    "welcome": '''
import json, re
names = [n["name"] for n in lcnb.INPUTS["notebooks"]]
paths = {n["name"]: n["path"] for n in lcnb.INPUTS["notebooks"]}

def html_text():
    return " ".join(str(w.value) for w in lcnb.all_widgets() if type(w).__name__ == "HTML")

def buttons(label):
    return [w for w in lcnb.all_widgets() if type(w).__name__ == "Button" and label.lower() in (w.description or "").lower()]

if any(type(w).__name__ == "Password" for w in lcnb.all_widgets()):
    lcnb.note("welcome_branch", "GitHub did not answer 200 for the version file: the notebook shows the personal-access-token form (private-repository branch)")
    load = lcnb.find(kind="Button", description="Load Private GitHub Repo")
    out = lcnb.click(load)
    lcnb.note("welcome_private_click", "clicked with an empty token: %s" % [w.value for w in lcnb.all_widgets() if type(w).__name__ == "HTML" and ("Failed" in str(w.value) or "Successfully" in str(w.value))][:1])
else:
    lcnb.note("welcome_branch", "GitHub answered 200: the table is shown directly")

text = html_text()
missing = [n for n in names if ("<div class='labconstrictor-table-cell labconstrictor-table-cell-center'>%s</div>" % n) not in text]
lcnb.check("oracle_welcome_rows", not missing, "the table has a row for each of the %d notebooks the app ships (%s)%s" % (len(names), ", ".join(names), "; MISSING: %s" % missing if missing else ""))
status = re.findall(r"(Up-to-date|Needs Update to [^<]*|Project Outdated|Missing Notebook)", text)
lcnb.note("welcome_status", "status cells: %s" % status)

opens = buttons("Open the notebook")
lcnb.check("oracle_welcome_open_buttons", len(opens) == len(names), "%d open buttons for %d notebooks" % (len(opens), len(names)))
seen = []
for button in opens:
    result = lcnb.guarded("click_open_button", lambda b=button: lcnb.click(b))
    if result is None:
        continue
    js = " ".join(str(o.get("application/javascript", "")) for o in result["outputs"])
    found = re.search(r'const notebookPath = ("[^"]*")', js)
    seen.append(json.loads(found.group(1)) if found else None)
lcnb.check("oracle_welcome_open_targets", sorted(map(str, seen)) == sorted(paths.values()), "open buttons target %s, construct.yaml ships %s" % (sorted(map(str, seen)), sorted(paths.values())))

updates = buttons("Update")
updates = [b for b in updates if "source" not in b.description.lower()]
for button in updates:
    result = lcnb.guarded("click_update_button", lambda b=button: lcnb.click(b))
    lcnb.note("welcome_update_click", "clicked an Update button (writes only into the scratch copy): %s" % [str(w.value)[:120] for w in lcnb.all_widgets() if type(w).__name__ == "HTML" and ("Updated" in str(w.value) or "Failed" in str(w.value) or "Error" in str(w.value))][:2])
if not updates:
    lcnb.note("welcome_update", "no Update button: every notebook is up to date or GitHub was not reachable")
if buttons("Update Source Code"):
    lcnb.human("click_update_source", "the 'Update Source Code' button runs pip install .. --force-reinstall in the app environment (network, and it replaces the installed package): not clicked")
''',
}


def inputs(ctx: Any) -> dict[str, Any]:
    """The notebooks the app ships (from construct.yaml of the checkout, not from the notebook under test) with the path the Welcome table must open."""
    construct = yaml.safe_load((ctx.src / "construct.yaml").read_text(encoding="utf-8"))
    shipped = []
    for entry in construct["extra_files"]:
        for source, destination in entry.items():
            if str(source).endswith(".ipynb") and Path(source).stem != "Welcome":
                shipped.append({"name": Path(source).stem, "path": str(source)})
    return {"notebooks": shipped}


NO_ORACLE = ""
