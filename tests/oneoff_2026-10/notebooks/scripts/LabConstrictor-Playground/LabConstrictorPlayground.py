"""Click script and oracle of LabConstrictorPlayground.ipynb: "Check everything" (a report in $HOME/LabConstrictorPlayground/reports, here the scratch home) and "Make test
data" (files of known content).

Clicks: Check everything with the speed test on and the internet off, then again with "Also try the internet" ticked (three connection probes: pypi.org, huggingface.co,
github.com, recorded in the sideeffects row); Make test data for every kind of the dropdown into a scratch folder.

Oracle (files on disk, recomputed here, not from the widgets): each report folder holds report.json (checks with layer, name, status, detail, fix), summary.txt and, because
the speed test ran, benchmark.png; no check has the status "fail" (a failing check of the app's own environment is a finding); the network layer has the 3 probes in the second
report only. Test data: three_channels.tif is (3,256,256) with the channel means 20 and 30 exactly for channels 2 and 3, rgb.tif has G=20 and B=30, labels.tif is a labelled image whose
largest label equals the number of distinct labels, timelapse.tif has 8 frames, points.csv has the header y,x,label."""

import json
from pathlib import Path
from typing import Any

AFTER_CELL = {4: "check", 6: "make"}
STAGES = {
    "check": '''
box_speed = lcnb.find(kind="Checkbox", description="speed test")
box_net = lcnb.find(kind="Checkbox", description="internet")
lcnb.check("click_check_defaults", box_speed.value is True and box_net.value is False, "defaults: speed test %s, internet %s (expected True, False)" % (box_speed.value, box_net.value))
button = lcnb.find(kind="Button", description="Check everything")
first = lcnb.click(button)
lcnb.check("click_check_report_message", "Report saved in" in first["stdout"], "output ends: %s" % first["stdout"].strip()[-160:])
lcnb.set_value(box_net, True)
second = lcnb.click(button)
lcnb.check("click_check_with_internet", "Report saved in" in second["stdout"], "second run with the internet probe: %s" % second["stdout"].strip()[-120:])
''',
    "make": '''
I = lcnb.INPUTS
lcnb.set_value(lcnb.find(kind="Text", description="Folder"), I["data_folder"])
dropdown = lcnb.find(kind="Dropdown", description="Kind")
button = lcnb.find(kind="Button", description="Make test data")
for kind in list(dropdown.options):
    lcnb.set_value(dropdown, kind)
    result = lcnb.guarded("click_make_" + kind, lambda: lcnb.click(button))
    lcnb.check("click_make_%s_listed" % kind, result is not None and ("three_channels" if kind == "all" else kind) in result["stdout"], "kind %s printed: %s" % (kind, (result or {"stdout": "(click failed)"})["stdout"].strip()[:150]))
''',
}


def inputs(ctx: Any) -> dict[str, Any]:
    return {"data_folder": str(ctx.work / "test_data")}


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import numpy as np
    import tifffile

    rows: list[tuple[str, str, str]] = []
    reports = sorted((ctx.home / "LabConstrictorPlayground" / "reports").glob("check_*"))
    rows.append(("two_report_folders", "PASS" if len(reports) == 2 else "FAIL", "%d report folders under the scratch home (2 clicks): %s" % (len(reports), [r.name for r in reports])))
    for number, folder in enumerate(reports):
        files = {n: (folder / n).is_file() for n in ("report.json", "summary.txt", "benchmark.png")}
        rows.append(("report_%d_files" % number, "PASS" if all(files.values()) else "FAIL", "%s: %s" % (folder.name, files)))
        if not files["report.json"]:
            continue
        checks = json.loads((folder / "report.json").read_text(encoding="utf-8"))["checks"]
        bad_shape = [c for c in checks if not {"layer", "name", "status", "detail", "fix"} <= set(c)]
        rows.append(("report_%d_rows" % number, "PASS" if len(checks) >= 5 and not bad_shape else "FAIL", "%d checks, layers %s, %d rows without the five columns" % (len(checks), sorted({c["layer"] for c in checks}), len(bad_shape))))
        failed = [c["layer"] + "/" + c["name"] + ": " + c["detail"][:80] for c in checks if c["status"] == "fail"]
        rows.append(("report_%d_no_fail" % number, "PASS" if not failed else "FAIL", "failed checks: %s" % (failed or "none")))
        network = [c for c in checks if c["layer"] == "network"]
        rows.append(("report_%d_network_probes" % number, "PASS" if len(network) == (3 if number == 1 else 0) else "FAIL", "%d network checks (expected %d for click %d): %s" % (len(network), 3 if number == 1 else 0, number + 1, [(c["name"], c["status"]) for c in network])))
        benchmark = [c for c in checks if c["layer"] == "benchmark"]
        rows.append(("report_%d_benchmark" % number, "PASS" if benchmark else "FAIL", "benchmark rows with the speed test on: %s" % [(c["name"], c["detail"][:30]) for c in benchmark]))
    data = ctx.work / "test_data"
    expected = {"three_channels.tif", "rgb.tif", "labels.tif", "timelapse.tif", "points.csv"}
    present = {p.name for p in data.glob("*")}
    rows.append(("test_data_files", "PASS" if present == expected else "FAIL", "files %s, expected %s" % (sorted(present), sorted(expected))))
    if "three_channels.tif" in present:
        stack = tifffile.imread(data / "three_channels.tif")
        rows.append(("three_channels_content", "PASS" if stack.shape == (3, 256, 256) and (stack[1] == 20).all() and (stack[2] == 30).all() and stack[0].mean() > 10 else "FAIL", "shape %s, channel means %s (channels 2 and 3 must be exactly 20 and 30)" % (stack.shape, [round(float(stack[i].mean()), 2) for i in range(len(stack))])))
    if "rgb.tif" in present:
        colour = tifffile.imread(data / "rgb.tif")
        rows.append(("rgb_content", "PASS" if colour.shape == (256, 256, 3) and colour.dtype == np.uint8 and (colour[..., 1] == 20).all() and (colour[..., 2] == 30).all() else "FAIL", "shape %s dtype %s, green %s blue %s" % (colour.shape, colour.dtype, np.unique(colour[..., 1])[:3], np.unique(colour[..., 2])[:3])))
    if "labels.tif" in present:
        labels = tifffile.imread(data / "labels.tif")
        distinct = len(np.unique(labels)) - 1
        rows.append(("labels_content", "PASS" if labels.shape == (256, 256) and distinct >= 1 and int(labels.max()) == distinct else "FAIL", "shape %s, %d labels, largest label %d (a labelled image numbers 1..N)" % (labels.shape, distinct, labels.max())))
    if "timelapse.tif" in present:
        movie = tifffile.imread(data / "timelapse.tif")
        rows.append(("timelapse_content", "PASS" if movie.shape == (8, 256, 256) else "FAIL", "shape %s (expected 8 frames of 256x256)" % (movie.shape,)))
    if "points.csv" in present:
        lines = (data / "points.csv").read_text(encoding="utf-8").splitlines()
        rows.append(("points_content", "PASS" if lines[0] == "y,x,label" and len(lines) > 1 else "FAIL", "header %r, %d rows" % (lines[0], len(lines) - 1)))
    return rows
