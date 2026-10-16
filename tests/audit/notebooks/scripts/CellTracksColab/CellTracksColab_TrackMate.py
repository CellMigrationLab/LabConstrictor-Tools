"""Click script and oracle of CellTracksColab_TrackMate.ipynb: the same analysis as the Custom notebook, loading TrackMate exports (<Condition>/<experiment>/FOV1_spots.csv and
FOV1_tracks.csv with TrackMate's three descriptive rows). Data and oracle: scripts/_ctc.py (Control speed 1.0, Mutant 2.0, 48 tracks, 960 spots, exact metrics). The loading cell is filled
(folder, 2D, csv, results folder, "Use test dataset" unticked: Zenodo download), every later button is pressed once with the notebook's defaults; "Find folder" is HUMAN.
"""

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
    "load": load_stage(
        {
            "Folder_path_widget": "I['folder']",
            "Data_Dims_widget": "2D",
            "File_Format_widget": "csv",
            "Results_Folder_widget": "I['results']",
        }
    )
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_dataset(ctx.work, "2D", "trackmate"))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    results = Path(_DATA["results"])
    rows = spots_rows(results, _DATA) + metric_rows(results, _DATA)
    rows += files_rows(results, {"QC/*": 1, "Tracks/*": 1, "track_parameters_plots/*": 2}, "files")
    balanced = sorted(results.glob("Balanced_dataset/merged_Tracks_balanced*.csv.gz"))
    count = len(pd.read_csv(balanced[0])) if balanced else -1
    rows.append(
        (
            "balanced_keeps_all_tracks",
            "PASS" if count == _DATA["n_tracks"] else "FAIL",
            "balanced dataset files %s: %d tracks (expected %d: already balanced)"
            % ([b.name for b in balanced], count, _DATA["n_tracks"]),
        )
    )
    return rows
