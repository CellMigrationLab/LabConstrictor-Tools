"""Click script and oracle of NucleiSky2DApp.ipynb (load images, segment + features, NucleiSky2D matching, adaptive matching, apply the saved transform).

Data: scripts/_nucleisky.py makes a 1200x1200 image of 300 blobs and a 400x400 crop cut at (y=300, x=500), pixel size 0.65 um in the TIFF tags (known geometry: no rotation,
scale 1, shift = |(300, 500)| px = 379.6 um). Segmentation method: the classical threshold (Cellpose and InstanSeg need model downloads: HUMAN).

Clicks: fill "Full Path", "Crop Path", "Folder" -> "Load & Process"; segmentation method "Auto-threshold" -> "Run Segmentation"; "Run NucleiSky2D" (default settings); the adaptive "run";
Step 3: transform path = the JSON the matching wrote, reference and crop paths -> "Inspect" -> confirm -> "Export".

Oracle: inputs_metadata.json carries the pixel sizes and paths we gave; the saved transform has scale 1 and a translation of the cut offset (length compared); the export wrote files."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _nucleisky import OFFSET_2D, PIXEL_UM, make_2d, setvars, status_check, transform_rows  # noqa: E402

AFTER_CELL = {6: "load", 8: "segment", 11: "match", 13: "adaptive", 16: "apply"}
STAGES = {
    "load": "I = lcnb.INPUTS\n" + "lcnb.set_value(lcnb.find(var='img_path'), I['full'])\nlcnb.set_value(lcnb.find(var='crop_path'), I['crop'])\nlcnb.set_value(lcnb.find(var='output_dir'), I['out'])\n"
    + "lcnb.click(lcnb.find(var='run_button'))\n" + status_check("status_html", "click_load_status", "Success"),
    "segment": "lcnb.set_value(lcnb.find(var='seg_method'), 'threshold')\nlcnb.click(lcnb.find(var='seg_btn'))\n" + status_check("seg_status", "click_segment_status")
    + "lcnb.human('click_segment_deep_learning', 'Cellpose and InstanSeg segmentation need model files (download) and a GPU for useful speed: not run, the threshold method is used')\n",
    "match": "lcnb.click(lcnb.find(var='run_btn'))\n" + status_check("matcher_status", "click_match_status"),
    "adaptive": "lcnb.click(lcnb.find(var='run_btn'))\n" + status_check("status_log", "click_adaptive_status"),
    "apply": '''
import json
from pathlib import Path
ns = get_ipython().user_ns
found = sorted(Path(str(ns["RESULT_DIR"])).rglob("*transform*.json"), key=lambda p: p.stat().st_mtime)
lcnb.check("click_apply_transform_found", bool(found), "transform files under RESULT_DIR: %s" % [p.name for p in found][:4])
I = lcnb.INPUTS
lcnb.set_value(lcnb.find(var="w_transform"), str(found[-1]))
lcnb.set_value(lcnb.find(var="w_ref_path"), I["full"])
lcnb.set_value(lcnb.find(var="w_mov_path"), I["crop"])
lcnb.set_value(lcnb.find(var="w_out_dir"), I["out"] + "_export")
lcnb.click(lcnb.find(var="b_inspect"))
lcnb.set_value(lcnb.find(var="w_confirm"), True)
lcnb.click(lcnb.find(var="run_button"))
''' + status_check("status_html", "click_apply_status", "complete"),
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_2d(ctx.work))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    out = Path(_DATA["out"])
    meta = out / "inputs_metadata.json"
    rows: list[tuple[str, str, str]] = []
    if meta.is_file():
        data = json.loads(meta.read_text(encoding="utf-8"))
        ok = abs(float(data.get("pixel_size_full", 0)) - PIXEL_UM) < 1e-3 and abs(float(data.get("pixel_size_crop", 0)) - PIXEL_UM) < 1e-3 and data.get("mode") == "external"
        rows.append(("inputs_metadata", "PASS" if ok else "FAIL", "inputs_metadata.json: %s (expected both pixel sizes %.2f um from the TIFF tags, mode external)" % ({k: data.get(k) for k in ("pixel_size_full", "pixel_size_crop", "mode")}, PIXEL_UM)))
    else:
        rows.append(("inputs_metadata", "FAIL", "%s was not written" % meta))
    shift = (OFFSET_2D[0] ** 2 + OFFSET_2D[1] ** 2) ** 0.5 * PIXEL_UM
    rows += transform_rows(out, 1.0, shift, 3 * PIXEL_UM, "matching")
    exported = [p for p in Path(_DATA["out"] + "_export").rglob("*") if p.is_file()] if Path(_DATA["out"] + "_export").is_dir() else []
    rows.append(("export_files", "PASS" if exported else "FAIL", "%d files exported by Step 3: %s" % (len(exported), [p.name for p in exported[:4]])))
    return rows
