"""Oracle of NucleiSky3D_API_Workflow_Example.ipynb: a script (no widgets). The notebook builds its own synthetic volume (96x160x160, 60 blobs) and, because no crop file exists,
a demo crop with a KNOWN random similarity transform (`ground_truth`, produced by generate_random_subvolume_3d). Nothing has to be edited.

Oracle (the notebook's own ground truth against the matcher output, written to a file by the harness): the pyramid or the hashing matcher succeeded and its scale equals the
ground-truth scale within 5 %; the QC overlay is a PNG and the aligned crop is a readable 3D TIFF in the notebook's output folder."""

import json
from pathlib import Path
from typing import Any

AFTER_CELL: dict[int, str] = {}
STAGES: dict[str, str] = {}
ORACLE_KERNEL = '''
import json
ns = get_ipython().user_ns
best = ns["best_result"]
json.dump({"gt_scale": float(ns["ground_truth"]["scale"]) if ns.get("ground_truth") else None, "best_scale": float(best["best_scale"]), "pyramid_success": bool(ns["result_pyramid"]["success"]),
           "hash_success": bool(ns["result_hash"]["success"]), "n_full": int(ns["labels_full"].max()), "n_crop": int(ns["labels_crop"].max())},
          open(str(ns["output_dir"].absolute()) + "/_nb_state.json", "w"))
'''


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import numpy as np
    import tifffile

    out = ctx.cwd / "nucleisky3d_output"
    state_file = out / "_nb_state.json"
    if not state_file.is_file():
        return [("state", "FAIL", "the harness could not read the matching results (the notebook did not reach its last cell): %s missing" % state_file)]
    state = json.loads(state_file.read_text())
    gt = state["gt_scale"]
    rows = [
        ("match_success", "PASS" if state["pyramid_success"] or state["hash_success"] else "FAIL", "pyramid success %s, hashing success %s" % (state["pyramid_success"], state["hash_success"])),
        ("scale_matches_ground_truth", "PASS" if gt and abs(state["best_scale"] - gt) <= 0.05 * gt else "FAIL", "recovered scale %.4f, ground truth %s (5 %% tolerance)" % (state["best_scale"], gt)),
        ("nuclei_found", "PASS" if state["n_full"] >= 30 and state["n_crop"] >= 5 else "FAIL", "labels: %d in the volume (60 blobs drawn, some merge), %d in the crop" % (state["n_full"], state["n_crop"])),
    ]
    png = out / "qc_overlay_3d.png"
    rows.append(("qc_overlay_png", "PASS" if png.is_file() and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" else "FAIL", "%s: %s bytes" % (png, png.stat().st_size if png.is_file() else "missing")))
    tif = out / "aligned_crop.tif"
    ok = tif.is_file() and tifffile.imread(tif).ndim == 3 and float(np.max(tifffile.imread(tif))) > 0
    rows.append(("aligned_crop_tif", "PASS" if ok else "FAIL", "%s is a readable non-empty 3D TIFF: %s" % (tif, ok)))
    return rows
