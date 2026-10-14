"""Click script and oracle of CellTracksColab_Viewer.ipynb (starts from existing CellTracksColab tables: view tracks, filter, compute metrics, QC, plots).

Data: scripts/_ctc.py writes merged_Tracks.csv and merged_Spots.csv (the columns the app's loader adds: Unique_ID, Condition, experiment_nb, Repeat, File_name, FRAME ...) for the same
48 straight tracks (Control speed 1.0, Mutant 2.0); the tracks table carries jittered metric columns that Part 4 must REPLACE with the exact values. Clicks: the loading cell (2D, track table,
spot table, results folder), then every button of every later cell once with the notebook's defaults. "Find file" buttons are HUMAN.
Oracle: after Part 4 merged_Tracks.csv.gz has Track Duration 19, Mean Speed 1.0 / 2.0, Total Distance Traveled 19 / 38, Directionality 1 for every track (the jitter is gone); QC and plot files exist."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _ctc import files_rows, load_stage, make_dataset, metric_rows  # noqa: E402

AUTO_DRIVE_ALL = True
AFTER_CELL = {6: "load"}
STAGES = {"load": load_stage({"Data_Dims_widget": "2D", "Track_table_widget": "I['track_table']", "Spot_table_widget": "I['spot_table']", "Results_Folder_widget": "I['results']"})}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_dataset(ctx.work, "2D", "custom"))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    results = Path(_DATA["results"])
    return metric_rows(results, _DATA) + files_rows(results, {"QC/*": 1, "track_parameters_plots/*/*": 1}, "files")
