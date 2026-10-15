"""Click script and oracle of CellTracksColab_Custom.ipynb (compile tracks from CSV files, map, calibrate, plot, filter, compute metrics, QC, plots).

Data: scripts/_ctc.py writes folder/<Condition>/<experiment>/FOV1.csv, 2 conditions x 3 experiments x 8 straight tracks of 20 spots (Control speed 1.0, Mutant speed 2.0 per frame; 48 tracks,
960 spots), so every metric has a known exact value. Clicks: the loading cell (folder, 2D, csv, results folder; "Use test dataset" UNTICKED: its default downloads an archive from Zenodo),
then every button of every later cell once, in order, with the notebook's own defaults (mapping Submit, calibration Submit with calibration off, "process all fields of view" Submit, filter,
rolling windows, similarity, plots). The native "Find folder" buttons are HUMAN (the path is typed instead).

Oracle (values recomputed from the construction): the saved merged_Spots has all 960 spots, 2 conditions, 48 tracks; after Part 4 merged_Tracks has Track Duration 19, Mean Speed 1.0 / 2.0,
Total Distance Traveled 19 / 38 and Directionality 1 for every track; the QC, plot and balanced-dataset files exist and the balanced dataset keeps all 48 tracks (it was balanced already)."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd  # noqa: E402
from _ctc import files_rows, load_stage, make_dataset, metric_rows, spots_rows  # noqa: E402

AUTO_DRIVE_ALL = True
AUTO_TICK = ("Mean Speed", "Total Distance Traveled")  # the plot cells need variables ticked, as a user would
AFTER_CELL = {7: "load"}
STAGES = {
    "load": load_stage({"Folder_path_widget": "I['folder']", "Data_Dims_widget": "2D", "File_Format_widget": "csv", "Results_Folder_widget": "I['results']"})
    + "lcnb.note('workaround_file_format', 'APP NOTEBOOK BUG: with Use test dataset unticked the Submit handler reads the global File_Format that only the test-dataset branch defines (NameError, FAIL row above). A user can define File_Format = \"csv\" in a cell: done here, and Submit is pressed again so that the rest of the notebook can be tested')\n"
    "get_ipython().user_ns['File_Format'] = 'csv'\n"
    "lcnb.guarded('click_load_submit_after_workaround', lambda: lcnb.click(lcnb.find(var='submit_button')))\n"
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_dataset(ctx.work, "2D", "custom"))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    results = Path(_DATA["results"])
    rows = spots_rows(results, _DATA) + metric_rows(results, _DATA)
    rows += files_rows(results, {"QC/*": 1, "Tracks/*": 1, "track_parameters_plots/*": 2}, "files")
    balanced = results / "Balanced_dataset" / "merged_Tracks_balanced_dataset.csv.gz"
    count = len(pd.read_csv(balanced)) if balanced.is_file() else -1
    rows.append(("balanced_keeps_all_tracks", "PASS" if count == _DATA["n_tracks"] else "FAIL", "%s has %d tracks (the dataset was already balanced: %d)" % (balanced.name, count, _DATA["n_tracks"])))
    return rows
