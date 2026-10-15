"""Click script and oracle of NucleiSky3DBenchmarking.ipynb (load a reference volume, 2.5D segmentation + 3D features, benchmark 3D patch matching, reload results, plots).

Data: the synthetic 48x160x160 volume of 70 blobs (scripts/_nucleisky.py), voxel size 1,1,1 um typed in the "Voxel Z,Y,X" field. Clicks: "Load reference volume" (path, voxel, result folder), threshold
segmentation -> run, then the notebook's own cells; the reload cell's "Load" button is pressed with the file the benchmark just wrote. The benchmark settings are REDUCED by a cell edit (NOTE row):
two patch shapes that fit the small volume, 3 patches per shape, matchers pyramid and hashing; the full-size benchmark is HUMAN (time, real data).

Oracle: the benchmark CSV has rows and only the matchers asked for; the saved config JSON lists the two patch shapes.
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _nucleisky import make_3d, status_check  # noqa: E402

AFTER_CELL = {5: "load", 6: "segment", 10: "reload"}
STAGES = {
    "load": "I = lcnb.INPUTS\nlcnb.set_value(lcnb.find(var='path_w'), I['full'])\nlcnb.set_value(lcnb.find(var='vox_w'), '1.0,1.0,1.0')\nlcnb.set_value(lcnb.find(var='outdir_w'), I['out'])\n"
    "lcnb.click(lcnb.find(var='inspect_btn'))\nlcnb.click(lcnb.find(var='load_btn'))\n"
    + status_check("status_html", "click_load_status"),
    "segment": "lcnb.set_value(lcnb.find(var='seg_method_w'), 'threshold')\nlcnb.click(lcnb.find(var='run_btn'))\n"
    + status_check("status_html", "click_segment_status")
    + "lcnb.human('click_segment_deep_learning', 'Cellpose and InstanSeg need model files (download) and a GPU: the threshold method is used')\n",
    "reload": "lcnb.click(lcnb.find(var='load_btn'))\nlcnb.note('click_reload', 'pressed Load with the csv and config paths the notebook proposes')\n",
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_3d(ctx.work))
    return dict(_DATA)


def edit_cells(ctx: Any) -> dict[int, list[tuple[str, str]]]:
    return {
        8: [
            ("(32, 192, 192),", "(32, 96, 96),"),
            ("(48, 256, 256),", "(40, 128, 128),"),
            ("PATCHES_PER_SHAPE_3D = 100", "PATCHES_PER_SHAPE_3D = 3"),
            ('    "adaptive",\n)\n\nmatcher_config_3d', ")\n\nmatcher_config_3d"),
        ]
    }


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import pandas as pd

    out = Path(_DATA["out"])
    rows: list[tuple[str, str, str]] = []
    csvs = sorted(out.rglob("*_benchmark3d_results.csv"))
    if not csvs:
        rows.append(("benchmark_csv", "FAIL", "no *_benchmark3d_results.csv under %s" % out))
    else:
        frame = pd.read_csv(csvs[0])
        matchers = set(frame["matcher"].astype(str)) if "matcher" in frame.columns else set()
        rows.append(
            (
                "benchmark_csv",
                "PASS" if len(frame) > 0 else "FAIL",
                "%s has %d rows" % (csvs[0].name, len(frame)),
            )
        )
        rows.append(
            (
                "benchmark_matchers",
                "PASS" if matchers == {"pyramid", "hashing"} else "FAIL",
                "matchers in the results: %s (asked for pyramid and hashing)" % sorted(matchers),
            )
        )
    configs = sorted(out.rglob("*_benchmark3d_config.json"))
    if configs:
        shapes = json.loads(configs[0].read_text())["patch_shapes_px_zyx_effective"]
        rows.append(
            (
                "config_shapes",
                "PASS" if shapes == [[32, 96, 96], [40, 128, 128]] else "FAIL",
                "effective patch shapes %s (asked for [32,96,96] and [40,128,128])" % shapes,
            )
        )
    else:
        rows.append(("config_shapes", "FAIL", "no *_benchmark3d_config.json under %s" % out))
    rows.append(
        (
            "full_benchmark",
            "HUMAN",
            "the benchmark at full size (hours on real data) is not run; this run used reduced settings",
        )
    )
    return rows
