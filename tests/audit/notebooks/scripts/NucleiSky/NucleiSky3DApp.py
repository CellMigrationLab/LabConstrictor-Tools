"""Click script and oracle of NucleiSky3DApp.ipynb (the 3D version of the app: load volumes, 2.5D segmentation + 3D features, NucleiSky3D matching, adaptive matching, apply a saved
transform).

Data: scripts/_nucleisky.py makes a 48x160x160 volume of 70 blobs and a 32x96x96 crop cut at (z=8, y=30, x=40), isotropic 1 um voxels given by hand (Full/Crop Z, Y, X).
Clicks: "Load & Process" (paths, folder, voxel sizes), "Run 2.5D Segment + Extract" with the threshold method, the matching "run", the adaptive "run", "Load transforms" and
"Apply & Export". Cellpose / InstanSeg: HUMAN (model download, GPU). Oracle: the saved transform has scale 1 and a translation of the cut offset (length), the export wrote files.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _nucleisky import OFFSET_3D, make_3d, setvars, status_check, transform_rows  # noqa: E402

AFTER_CELL = {6: "load", 8: "segment", 11: "match", 13: "adaptive", 16: "apply"}
STAGES = {
    "load": "I = lcnb.INPUTS\n"
    + setvars({"full_path": "@full", "crop_path": "@crop", "output_dir": "@out"})
    .replace("'@full'", "I['full']")
    .replace("'@crop'", "I['crop']")
    .replace("'@out'", "I['out']")
    + setvars(
        {
            "vox_full_z": 1.0,
            "vox_full_y": 1.0,
            "vox_full_x": 1.0,
            "vox_crop_z": 1.0,
            "vox_crop_y": 1.0,
            "vox_crop_x": 1.0,
        }
    )
    + "lcnb.click(lcnb.find(var='run_button'))\n"
    + status_check("status_html", "click_load_status"),
    "segment": "lcnb.set_value(lcnb.find(var='seg_method'), 'threshold')\nlcnb.click(lcnb.find(var='run_btn'))\n"
    + status_check("status_html", "click_segment_status")
    + "lcnb.human('click_segment_deep_learning', 'Cellpose and InstanSeg segmentation need model files (download) and a GPU: not run, the threshold method is used')\n",
    "match": "lcnb.guarded('click_match_unmodified', lambda: lcnb.click(lcnb.find(var='run_btn')))\nlcnb.note('click_match_full_output', (lcnb.LAST_OUTPUT.get('stdout', '') + lcnb.LAST_OUTPUT.get('stderr', '')).replace(chr(10), ' | ')[-2500:])\n"
    "lcnb.note('workaround_plot_warp_overlay3D', 'APP NOTEBOOK BUG: the notebook imports plot_warp_overlay3d (lower d) but calls plot_warp_overlay3D (NameError inside the matcher loop: pyramid crashed, nothing exported). A user can define the alias in a cell: done here, and Run is pressed again so that the rest of the notebook can be tested')\n"
    "from_ns = get_ipython().user_ns\nfrom_ns['plot_warp_overlay3D'] = from_ns['plot_warp_overlay3d']\n"
    "lcnb.click(lcnb.find(var='run_btn'))\n"
    + status_check("status_html", "click_match_status_after_workaround", "Results saved"),
    "adaptive": "try:\n    lcnb.click(lcnb.find(var='run_btn'))\nfinally:\n    lcnb.note('click_adaptive_full_output', (lcnb.LAST_OUTPUT.get('stdout', '') + lcnb.LAST_OUTPUT.get('stderr', '')).replace(chr(10), ' | ')[-2500:])\n"
    + status_check("status_log", "click_adaptive_status"),
    "apply": """
from pathlib import Path
ns = get_ipython().user_ns
found = sorted(Path(str(ns["RESULT_DIR"])).rglob("*transform*.json"), key=lambda p: p.stat().st_mtime)
lcnb.check("click_apply_transform_found", bool(found), "transform files under RESULT_DIR: %s" % [p.name for p in found][:4])
I = lcnb.INPUTS
lcnb.set_value(lcnb.find(var="transform_path"), str(found[-1]))
lcnb.click(lcnb.find(var="load_btn"))
lcnb.set_value(lcnb.find(var="full_path"), I["full"])
lcnb.set_value(lcnb.find(var="crop_path"), I["crop"])
lcnb.set_value(lcnb.find(var="out_dir"), I["out"] + "_export")
lcnb.click(lcnb.find(var="apply_btn"))
""",
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_3d(ctx.work))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    shift = sum(o**2 for o in OFFSET_3D) ** 0.5
    rows = transform_rows(Path(_DATA["out"]), 1.0, shift, 3.0, "matching")
    export = Path(_DATA["out"] + "_export")
    exported = [p for p in export.rglob("*") if p.is_file()] if export.is_dir() else []
    rows.append(
        (
            "export_files",
            "PASS" if exported else "FAIL",
            "%d files exported by Step 3: %s" % (len(exported), [p.name for p in exported[:4]]),
        )
    )
    return rows
