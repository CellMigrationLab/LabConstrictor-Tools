"""Click script and oracle of NucleiSky2DBenchmarking.ipynb (load an image, segment it, benchmark matching on random patches, plot, a segmentation-error benchmark, plots).

Data: the synthetic 1200x1200 image of 300 blobs of scripts/_nucleisky.py (0.65 um/px). Clicks: "Load & Process" (path, results folder), threshold segmentation -> "Run Segmentation".
The benchmark cells are designed for hours on real data (10 patch sizes x 50 patches x 5 matchers; the segmentation-error benchmark 8 x 8 perturbations): as a user would to try the
notebook, the script REDUCES their settings (edits are NOTE rows: patch sizes 128 and 256, 3 patches, matchers graph and quad; 2 patches, quad, missed 0/20 %, extra 0/50 %). The result is
not a benchmark of NucleiSky, only a run of the benchmark code; the full-size benchmark is HUMAN (time).

Oracle: the benchmark CSV has rows, only the two matchers asked for and only the two patch sizes asked for; the segmentation-error benchmark wrote its summary files.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _nucleisky import make_2d, status_check  # noqa: E402

AFTER_CELL = {5: "load", 6: "segment", 14: "reload_seg"}
SEG_OUT_CHECK = (
    "_m = get_ipython().user_ns.get('masks_full')\n"
    "lcnb.check('click_segment_status', _m is not None and int(_m.max()) >= 250, 'the segmentation button produced masks_full with %s nuclei (300 blobs drawn); the notebook prints its status into an Output widget that a headless kernel does not keep' % (None if _m is None else int(_m.max())))\n"
)
STAGES = {
    "load": "I = lcnb.INPUTS\nlcnb.set_value(lcnb.find(var='img_path'), I['full'])\nlcnb.set_value(lcnb.find(var='out_dir_input'), I['out'])\nlcnb.click(lcnb.find(var='run_button'))\n"
    + status_check("status_html", "click_load_status"),
    "segment": "lcnb.set_value(lcnb.find(var='seg_method'), 'threshold')\nlcnb.click(lcnb.find(var='seg_btn'))\n"
    + SEG_OUT_CHECK
    + "lcnb.human('click_segment_deep_learning', 'Cellpose and InstanSeg need model files (download) and a GPU: the threshold method is used')\n",
    "reload_seg": "lcnb.click(lcnb.find(var='load_button'))\nlcnb.note('click_reload_seg', 'pressed Load results with the default folder the notebook proposes')\n",
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_2d(ctx.work))
    return dict(_DATA)


def edit_cells(ctx: Any) -> dict[int, list[tuple[str, str]]]:
    return {
        8: [
            ("patch_sizes_px=[50, 75, 100, 128, 192, 256, 320, 384, 448, 512]", "patch_sizes_px=[128, 256]"),
            ("patches_per_size=50", "patches_per_size=3"),
            ('matchers=("graph", "quad", "triangles", "hashing", "adaptive")', 'matchers=("graph", "quad")'),
        ],
        13: [
            ("PATCHES_PER_SIZE = 20", "PATCHES_PER_SIZE = 2"),
            ("MIN_CLEAN_NUCLEI_PER_PATCH = 50", "MIN_CLEAN_NUCLEI_PER_PATCH = 10"),
            ('MATCHERS = ("quad", "triangles", "hashing")', 'MATCHERS = ("quad",)'),
            ("MISSED_NUCLEI_PCT = [0, 10, 20, 40, 60, 80, 90, 95]", "MISSED_NUCLEI_PCT = [0, 20]"),
            ("EXTRA_DETECTIONS_PCT = [0, 10, 25, 50, 100, 200, 500, 1000]", "EXTRA_DETECTIONS_PCT = [0, 50]"),
        ],
    }


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import pandas as pd

    out = Path(_DATA["out"])
    rows: list[tuple[str, str, str]] = []
    csvs = sorted(out.rglob("*_benchmark_results.csv"))
    if not csvs:
        rows.append(("benchmark_csv", "FAIL", "no *_benchmark_results.csv under %s" % out))
    else:
        frame = pd.read_csv(csvs[0])
        matchers = set(frame["matcher"].astype(str)) if "matcher" in frame.columns else set()
        rows.append(
            (
                "benchmark_csv",
                "PASS" if len(frame) > 0 else "FAIL",
                "%s has %d rows, columns %s" % (csvs[0].name, len(frame), list(frame.columns)[:8]),
            )
        )
        rows.append(
            (
                "benchmark_matchers",
                "PASS" if matchers == {"graph", "quad"} else "FAIL",
                "matchers in the results: %s (asked for graph and quad)" % sorted(matchers),
            )
        )
        size_col = next((c for c in frame.columns if "patch" in c.lower() and "size" in c.lower()), None)
        sizes = set(frame[size_col]) if size_col else set()
        rows.append(
            (
                "benchmark_patch_sizes",
                "PASS" if (sizes and sizes <= {128, 256}) or (not size_col and len(frame) == 12) else "FAIL",
                "patch sizes in column %s: %s (asked for 128 and 256); the table has no patch-size column, so its %d rows are compared with 2 sizes x 3 patches x 2 matchers = 12"
                % (size_col, sorted(sizes), len(frame)),
            )
        )
    seg = sorted(out.rglob("*missed_extra_ssim_only_512_summary.csv"))
    rows.append(
        (
            "segmentation_error_summary",
            "PASS" if seg and seg[0].stat().st_size > 0 else "FAIL",
            "segmentation-error summary files: %s" % [p.name for p in seg],
        )
    )
    rows.append(
        (
            "full_benchmark",
            "HUMAN",
            "the benchmark at full size (hours on real data) is not run; this run used reduced settings",
        )
    )
    return rows
