"""Click script and oracle of CellTracksColab_Distance_to_ROI.ipynb (distance of every spot to the nearest ROI of a mask image, then metrics, QC, plots, classification by distance).

Data: scripts/_ctc.py: the CellTracksColab tables (48 tracks) and, per field of view, a 200x200 mask `<File_name>_nuclei.tif` with one disc (centre (100,100), radius 20 px); pixel calibration 0.5
um/px. Clicks: loading cell, then the ROI cell (the later cells 40 and 42 have their own ROI name field with the default "edge": set to nuclei; distance threshold 10 um) (ROI folder, ROI name nuclei, pixel calibration 0.5), then every button once with the defaults. "Find folder" / "Find file" are HUMAN.
Oracle: the distance of every saved spot equals the Euclidean distance transform of the mask at the pixel of the spot, times 0.5, recomputed here with scipy (not the notebook's number).
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _ctc import ROI_CAL, ROI_NAME, files_rows, load_stage, make_dataset  # noqa: E402

AUTO_DRIVE_ALL = True
AUTO_TICK = ("Mean Speed", "Total Distance Traveled")  # the plot cells need variables ticked, as a user would
AFTER_CELL = {6: "load", 11: "roi", 40: "roi_name", 42: "classify"}
STAGES = {
    "load": load_stage(
        {
            "Data_Dims_widget": "2D",
            "Track_table_widget": "I['track_table']",
            "Spot_table_widget": "I['spot_table']",
            "Results_Folder_widget": "I['results']",
        }
    ),
    "roi": "I = lcnb.INPUTS\nlcnb.set_value(lcnb.find(var='ROI_folder_widget'), I['roi'])\nlcnb.set_value(lcnb.find(var='ROI_name_widget'), %r)\nlcnb.set_value(lcnb.find(var='Pixel_calibration_widget'), %r)\nlcnb.auto_drive('roi')\n"
    % (ROI_NAME, ROI_CAL),
    "roi_name": "lcnb.set_value(lcnb.find(var='ROI_name_widget'), %r)\nlcnb.auto_drive('roi_name')\n"
    % ROI_NAME,
    "classify": "lcnb.set_value(lcnb.find(var='ROI_name_widget'), %r)\nlcnb.set_value(lcnb.find(var='distance_threshold_widget'), 10.0)\nlcnb.auto_drive('classify')\n"
    % ROI_NAME,
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_dataset(ctx.work, "2D", "custom"))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import numpy as np
    import pandas as pd
    import tifffile
    from scipy.ndimage import distance_transform_edt

    results = Path(_DATA["results"])
    path = results / "merged_Spots.csv.gz"
    column = "DistanceTo" + ROI_NAME
    if not path.is_file():
        return [("distance_spots_file", "FAIL", "%s was not written" % path)]
    spots = pd.read_csv(path, low_memory=False)
    if column not in spots.columns:
        return [
            (
                "distance_column",
                "FAIL",
                "column %s is not in %s (columns: %s)" % (column, path.name, list(spots.columns)[-8:]),
            )
        ]
    expected = np.full(len(spots), np.nan)
    for name, group in spots.groupby("File_name"):
        mask = tifffile.imread(Path(_DATA["roi"]) / ("%s_%s.tif" % (name, ROI_NAME)))
        transform = distance_transform_edt(mask == 0) * ROI_CAL
        y = (group["POSITION_Y"] / ROI_CAL).astype(int).clip(0, mask.shape[0] - 1)
        x = (group["POSITION_X"] / ROI_CAL).astype(int).clip(0, mask.shape[1] - 1)
        expected[spots.index.get_indexer(group.index)] = transform[y, x]
    error = float(np.nanmax(np.abs(spots[column].to_numpy(float) - expected)))
    rows = [
        (
            "distance_matches_edt",
            "PASS" if error < 1e-6 else "FAIL",
            "max |notebook distance - recomputed EDT distance| = %.3g over %d spots" % (error, len(spots)),
        )
    ]
    tracks_path = results / "merged_Tracks.csv.gz"
    tracks = pd.read_csv(tracks_path, low_memory=False) if tracks_path.is_file() else pd.DataFrame()
    label = "Track_Classification_" + ROI_NAME
    counts = tracks[label].value_counts().to_dict() if label in tracks.columns else {}
    rows.append(
        (
            "classification_covers_all_tracks",
            "PASS" if sum(counts.values()) == _DATA["n_tracks"] else "FAIL",
            "column %s counts %s (every one of the %d tracks must be classified)"
            % (label, counts, _DATA["n_tracks"]),
        )
    )
    return rows + files_rows(results, {"Distance_to_ROI/**/*.pdf": 1}, "files")
