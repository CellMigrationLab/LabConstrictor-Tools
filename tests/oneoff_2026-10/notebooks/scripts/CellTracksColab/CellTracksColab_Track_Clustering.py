"""Click script and oracle of CellTracksColab_Track_Clustering.ipynb (Ripley's L function of the track positions per field of view, Monte Carlo envelopes, comparison across conditions).

Data: the CellTracksColab tables of scripts/_ctc.py (6 fields of view, 8 tracks each). Clicks: the loading cell (2D, tables, results folder), then every later button once with the defaults
(settings check, Monte Carlo with 10 simulations, plots, the specific-radius analysis). Oracle: the files the notebook writes exist (Ripley L per FOV and the coordinate plots, one per field of
view) and the loaded spot count in the Results table is the number we built (960)."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _ctc import files_rows, load_stage, make_dataset  # noqa: E402

AUTO_DRIVE_ALL = True
AFTER_CELL = {6: "load"}
STAGES = {"load": load_stage({"Data_Dims_widget": "2D", "Track_table_widget": "I['track_table']", "Spot_table_widget": "I['spot_table']", "Results_Folder_widget": "I['results']"})}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_dataset(ctx.work, "2D", "custom"))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    results = Path(_DATA["results"])
    return files_rows(results, {"Track_Clustering/RipleyL/*": 1, "Track_Clustering/Coordinates/*": 6}, "files")
