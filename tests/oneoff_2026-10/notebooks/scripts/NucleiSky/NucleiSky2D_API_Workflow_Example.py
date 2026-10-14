"""Oracle of NucleiSky2D_API_Workflow_Example.ipynb: a script (no widgets). The configuration cell holds the placeholder `path/to/your/data` and two file names: as a user must,
the script edits that cell to point at the synthetic data of scripts/_nucleisky.py (1200x1200 image with 300 blobs, 400x400 crop cut at y=300, x=500, 0.65 um/px, no rotation).

Oracle (geometry we cut the crop with, not the notebook's variables): the segmentation finds about as many nuclei as we drew (300 in the image, those inside the crop in the crop),
the saved manual transform has scale 1 and a translation of length |(300, 500)| px * 0.65 um, and the export folder holds files."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _nucleisky import OFFSET_2D, PIXEL_UM, make_2d, transform_rows  # noqa: E402

AFTER_CELL: dict[int, str] = {}
STAGES: dict[str, str] = {}
ORACLE_KERNEL = '''
import json
ns = get_ipython().user_ns
json.dump({"n_full": int(len(ns["df_full"])), "n_crop": int(len(ns["df_crop"])), "adaptive_success": bool(ns["best_result_adaptive"]["success"]), "manual_success": bool(ns["manual_result"]["success"])},
          open(str(ns["output_dir"].absolute()) + "/_nb_state.json", "w"))
'''
_DATA: dict[str, Any] = {}


def edit_cells(ctx: Any) -> dict[int, list[tuple[str, str]]]:
    _DATA.update(make_2d(ctx.work))
    folder = str(Path(_DATA["full"]).parent)
    return {3: [("Path(\"path/to/your/data\")", "Path(%r)" % folder), ("reference_image.tif", "full.tif"), ("crop_image.tif", "crop.tif")]}


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    out = ctx.cwd / "nucleisky_output"
    state_file = out / "_nb_state.json"
    state = json.loads(state_file.read_text()) if state_file.is_file() else {}
    rows = [
        ("nuclei_counts", "PASS" if state and abs(state["n_full"] - _DATA["nuclei"]) <= 0.1 * _DATA["nuclei"] and abs(state["n_crop"] - _DATA["nuclei_in_crop"]) <= 3 else "FAIL",
         "segmented %s nuclei in the image (drawn %d) and %s in the crop (drawn inside it: %d)" % (state.get("n_full"), _DATA["nuclei"], state.get("n_crop"), _DATA["nuclei_in_crop"])),
        ("manual_match_success", "PASS" if state.get("manual_success") else "FAIL", "manual QUAD matcher success flag %s" % state.get("manual_success")),
    ]
    rows += transform_rows(out, 1.0, (OFFSET_2D[0] ** 2 + OFFSET_2D[1] ** 2) ** 0.5 * PIXEL_UM, 3 * PIXEL_UM, "manual")
    exported = [p for p in (out / "aligned_images").rglob("*") if p.is_file()] if (out / "aligned_images").is_dir() else []
    rows.append(("export_files", "PASS" if exported else "FAIL", "%d files in aligned_images: %s" % (len(exported), [p.name for p in exported[:4]])))
    return rows
