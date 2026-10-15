#!/usr/bin/env python3
"""Turn the output of check_ground_truth.py (CHECK/NOTE lines) into a matrix file (family synthetic).
usage: syn_to_matrix.py APP HOST CHECK_OUTPUT_TXT OUTDIR [REPORTS_DIR]
With REPORTS_DIR (a host run): a dataset whose case the form could not hold (not_expressible.json) or that the form refused before any run ('Run did not start a task; status: <warning>')
is not a failure of the tool: its rows become NOTE rows that say so (not green, not red)."""
import json, re, sys
sys.path.insert(0, "/home/user/wt_a2/tests/oneoff_2026-10")
from pathlib import Path
from matrix import Matrix
app, host, txt, out = sys.argv[1:5]
reports = Path(sys.argv[5]) if len(sys.argv) > 5 else None
special = {}
if reports is not None:
    p = reports / "not_expressible.json"
    if p.is_file():
        for x in json.loads(p.read_text()):
            if x.get("dataset"): special[x["dataset"]] = "the form cannot hold the value (%s)" % x["why"][:150]
    for f in reports.glob("*.json"):
        if f.name.startswith("case_") or f.name in ("cases_summary.json", "not_expressible.json"): continue
        try: d = json.loads(f.read_text())
        except ValueError: continue
        e = str(d.get("error") or "")
        if d.get("status") == "DRIVER_ERROR" and "Run did not start a task; status:" in e:
            special[f.stem] = "the form itself refused the input with a sentence before any run: %s" % re.sub(r"\s+", " ", e.split("status:", 1)[1].split("|")[0]).strip()[:200]
m = Matrix(Path(out), "synthetic", host, app)
pre = "syn_" if host == "cli" else "syn_host_%s_" % host
dataset_ids = sorted(special, key=len, reverse=True)
for line in Path(txt).read_text(encoding="utf-8", errors="replace").splitlines():
    g = re.match(r"^CHECK\s+(\S+)\s+(PASS|FAIL|NOT_RUN)\s*(.*)$", line)
    if g:
        cid, st, detail = g.groups()
        why = next((special[d] for d in dataset_ids if cid.startswith(d + "_")), None)
        if host != "cli" and re.match(r"^\w+_cli_\d+_", cid) and st != "PASS":   # a dataset id ending _cli: the CLI/worker expectation (no channel chooser); a host has one and picks a channel
            why = "CLI-only expectation (worker without the host's channel chooser); the host picks a channel itself and ran the tool"
        tool = re.sub(r"_\d+_.*$", "", cid)
        if why and st != "PASS":
            m.add(pre + cid, "NOTE", why, tool=tool)
        else:
            m.add(pre + cid, st, detail, tool=tool)
        continue
    g = re.match(r"^NOTE\s+(\S+)\s+(.*)$", line)
    if g:
        st = "HUMAN" if "HUMAN" in g.group(2) or "judged by a person" in g.group(2) else "NOTE"
        m.add(pre + g.group(1) + "_note", st, g.group(2), tool=g.group(1))
print(m.finish())
