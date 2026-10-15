"""Click script and oracle of CellTracksColab_TrackMate_Plate.ipynb (a plate: wells instead of conditions; the notebook maps wells to conditions with one text field per well).

Data: scripts/_ctc.py `make_plate`: A01_1-spots.csv / A01_1-tracks.csv ... for wells A01 A02 (built with speed 1.0) and B01 B02 (speed 2.0), 8 tracks of 20 spots each. Clicks: the loading cell
(folder, results folder), then the mapping: "Well A01" and "Well A02" = Control, "Well B01" and "Well B02" = Mutant -> "Update Conditions"; every later button once with the defaults.
Oracle: after the mapping and Part 4 the mean speed per Condition is 1.0 (Control) and 2.0 (Mutant) with 16 tracks each."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _ctc import WELLS, condition_speed_rows, files_rows, load_stage, make_plate  # noqa: E402

AUTO_DRIVE_ALL = True
AUTO_TICK = ("Mean Speed", "Total Distance Traveled")  # the plot cells need variables ticked, as a user would
AFTER_CELL = {7: "load", 9: "map"}
STAGES = {
    "load": load_stage({"Folder_path_widget": "I['folder']", "Results_Folder_widget": "I['results']"}),
    "map": "".join("lcnb.set_value(lcnb.find(kind='Text', description='Well %s'), %r)\n" % (well, condition) for well, condition in WELLS.items())
    + "lcnb.click(lcnb.find(kind='Button', description='Update Conditions', exact=True))\n"
    + "lcnb.check('click_map_conditions', set(get_ipython().user_ns['merged_tracks_df']['Condition']) == {'Control', 'Mutant'}, 'conditions after the mapping: %s' % sorted(set(get_ipython().user_ns['merged_tracks_df']['Condition'])))\n",
}
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_plate(ctx.work))
    return dict(_DATA)


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    results = Path(_DATA["results"])
    return condition_speed_rows(results) + files_rows(results, {"QC/*": 1}, "files")
